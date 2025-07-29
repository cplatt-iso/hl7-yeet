# --- START OF FILE app/routes/auth_routes.py ---
import os
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from pydantic import ValidationError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .. import schemas, crud
from ..extensions import db, bcrypt # Correct imports

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        user_data = schemas.UserCreate.model_validate(request.get_json())
    except ValidationError as e:
        # We can add logging here too, for good measure
        logging.error(f"Validation error on /register: {e.errors()}")
        return jsonify({"error": e.errors()}), 422

    if crud.get_user_by_username(db, user_data.username) or crud.get_user_by_email(db, user_data.email):
        return jsonify({"error": "Username or email already exists"}), 409

    user = crud.create_user(db, user_data)
    return jsonify({"message": f"User {user.username} created successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        login_data = schemas.UserLogin.model_validate(request.get_json())
    except ValidationError as e:
        logging.error(f"Validation error on /login: {e.errors()}")
        return jsonify({"error": e.errors()}), 422

    user = crud.get_user_by_username(db, login_data.username)
    if user and bcrypt.check_password_hash(user.password_hash, login_data.password):
        # --- FIX: Cast the user ID to a string ---
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token, username=user.username)
    
    return jsonify({"error": "Invalid username or password"}), 401

@auth_bp.route('/google', methods=['POST'])
def google_auth():
    try:
        token_data = schemas.GoogleToken.model_validate(request.get_json())
    except ValidationError as e:
        logging.error(f"Validation error on /google: {e.errors()}")
        return jsonify({"error": e.errors()}), 422
    
    google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
    if not google_client_id:
        logging.error("FATAL: GOOGLE_CLIENT_ID is not configured on the server.")
        return jsonify({"error": "Server is not configured for Google login."}), 500
        
    try:
        id_info = id_token.verify_oauth2_token(token_data.token, google_requests.Request(), google_client_id)
        google_user_id = id_info['sub']
        email = id_info['email']

        user = crud.get_user_by_google_id(db, google_user_id)
        if not user:
            if crud.get_user_by_email(db, email):
                return jsonify({"error": "This email is already registered. Please log in normally."}), 409
            
            username = id_info.get('name', email.split('@')[0])
            user = crud.create_google_user(db, email=email, username=username, google_id=google_user_id)

        # --- FIX: Cast the user ID to a string ---
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token, username=user.username)

    except ValueError as e:
        logging.exception("Google token verification failed:")
        return jsonify({"error": f"Invalid Google token: {e}"}), 401
    except Exception as e:
        logging.exception(f"An unexpected error occurred during Google auth:")
        return jsonify({"error": "An internal server error occurred"}), 500
# --- END OF FILE app/routes/auth_routes.py ---