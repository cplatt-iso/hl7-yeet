# --- START OF FILE app/routes/admin_routes.py ---

import os
import logging
from functools import wraps
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from werkzeug.utils import secure_filename

from ..extensions import db, socketio # <-- IMPORT socketio
from .. import crud, schemas
from ..util import definition_processor
from ..models import User
from ..schemas import UserSchema
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

def admin_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user = crud.get_user_by_id(db, current_user_id)
            if not user or not user.is_admin:
                logging.warning(f"Non-admin user {user.username if user else 'Unknown'} with ID {current_user_id} tried to access an admin route.")
                return jsonify(msg="Admins only! Fuck off!"), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

# ... (Version management routes are unchanged) ...
@admin_bp.route('/versions', methods=['GET'])
@admin_required()
def get_versions():
    versions = crud.get_all_hl7_versions(db)
    return jsonify([schemas.Hl7VersionResponse.model_validate(v).model_dump() for v in versions]), 200

@admin_bp.route('/versions/upload', methods=['POST'])
@admin_required()
def upload_version():
    if 'file' not in request.files: return jsonify(error="No file part in the request"), 400
    file = request.files['file']
    version_string = request.form.get('version')
    description = request.form.get('description', '')
    if not file or not file.filename: return jsonify(error="No file selected for uploading"), 400
    if not version_string: return jsonify(error="Version string is required"), 400
    filename = secure_filename(file.filename)
    if not filename.endswith('.zip'): return jsonify(error="Invalid file type. Please upload a ZIP file."), 400
    upload_folder = current_app.config['UPLOAD_FOLDER']
    saved_path = os.path.join(upload_folder, filename)
    file.save(saved_path)
    current_user_id = get_jwt_identity()
    logging.info(f"Starting processing for version '{version_string}' uploaded by user {current_user_id}...")
    result = definition_processor.process_version_upload(saved_path, version_string, description, current_user_id)
    if result['status'] == 'success': return jsonify(result), 200
    else: return jsonify(error=result['message']), 500

@admin_bp.route('/versions/<int:version_id>/toggle', methods=['PATCH'])
@admin_required()
def toggle_version_status(version_id):
    version = crud.toggle_hl7_version_status(db, version_id)
    if not version: return jsonify(error="Version not found"), 404
    return jsonify(schemas.Hl7VersionResponse.model_validate(version).model_dump()), 200

@admin_bp.route('/versions/<int:version_id>/default', methods=['PATCH'])
@admin_required()
def set_default_version(version_id):
    version = crud.set_default_hl7_version(db, version_id)
    if not version:
        return jsonify(error="Version not found or could not be set as default"), 404
    return jsonify(schemas.Hl7VersionResponse.model_validate(version).model_dump()), 200

# --- NEW ENDPOINT ---
@admin_bp.route('/terminology/status', methods=['GET'])
@admin_required()
def get_terminology_status():
    """Returns statistics about the currently loaded terminology."""
    stats = crud.get_terminology_stats(db)
    return jsonify(stats)

@admin_bp.route('/terminology/refresh', methods=['POST'])
@admin_required()
def refresh_terminology():
    """Triggers a full refresh of V2 terminology tables."""
    current_user_id = get_jwt_identity()
    logging.info(f"Admin user {current_user_id} triggered a terminology refresh.")
    
    # Capture the app instance while we're still in request context
    app = current_app._get_current_object()  # type: ignore
    
    # Wrapper function to run the refresh with Flask app context
    def run_refresh():
        try:
            # Background tasks need the Flask app context for database operations
            with app.app_context():
                definition_processor.process_terminology_refresh(socketio)
        except Exception as e:
            logging.error(f"Background terminology refresh failed: {e}", exc_info=True)
    
    # Run the terminology refresh as a background task to avoid blocking the request
    socketio.start_background_task(run_refresh)
    
    # Return immediately with 202 Accepted - client will receive updates via Socket.IO
    return jsonify({"status": "started", "message": "Terminology refresh started in background"}), 202

@admin_bp.route('/terminology/tables', methods=['GET'])
@admin_required()
def get_all_table_ids():
    """Returns a list of all unique table IDs."""
    table_ids = crud.get_distinct_table_ids(db)
    return jsonify(table_ids)

@admin_bp.route('/terminology/tables/<string:table_id>', methods=['GET'])
@admin_required()
def get_table_details(table_id):
    """Returns all definitions for a given table ID."""
    definitions = crud.get_definitions_for_table(db, table_id)
    return jsonify([schemas.Hl7TableDefinitionResponse.model_validate(d).model_dump() for d in definitions])

@admin_bp.route('/terminology/definitions', methods=['POST'])
@admin_required()
def add_definition():
    """Adds a new definition to a table."""
    try:
        data = schemas.DefinitionCreate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422
    
    new_def = crud.create_definition(db, data)
    return jsonify(schemas.Hl7TableDefinitionResponse.model_validate(new_def).model_dump()), 201

@admin_bp.route('/terminology/definitions/<int:def_id>', methods=['PUT'])
@admin_required()
def edit_definition(def_id):
    """Updates an existing definition."""
    try:
        data = schemas.DefinitionUpdate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422

    updated_def = crud.update_definition(db, def_id, data)
    if not updated_def:
        return jsonify({"error": "Definition not found"}), 404
    return jsonify(schemas.Hl7TableDefinitionResponse.model_validate(updated_def).model_dump())

@admin_bp.route('/terminology/definitions/<int:def_id>', methods=['DELETE'])
@admin_required()
def remove_definition(def_id):
    """Deletes a definition."""
    success = crud.delete_definition(db, def_id)
    if not success:
        return jsonify({"error": "Definition not found"}), 404
    return '', 204 # No Content

@admin_bp.route('/users', methods=['GET'])
@admin_required()
def get_users():
    """Gets a list of all users."""
    users = User.query.all()
    # Use the UserSchema you imported to serialize the data
    return jsonify([UserSchema.from_orm(u).model_dump() for u in users])

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required()
def delete_user(user_id):
    """Deletes a user by their ID."""
    # The admin_required decorator already confirms the current user is an admin.
    user_to_delete = User.query.get(user_id)
    if not user_to_delete:
        return jsonify({"msg": "User not found"}), 404
    
    # Prevent an admin from deleting themselves
    current_user_id = get_jwt_identity()
    if user_to_delete.id == int(current_user_id):
         return jsonify({"msg": "Admin cannot delete themselves."}), 400

    db.session.delete(user_to_delete)
    db.session.commit()
    return jsonify({"msg": "User deleted successfully"}), 200

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required()
def update_user(user_id):
    """Updates a user's admin status."""
    user_to_update = User.query.get(user_id)
    if not user_to_update:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json()
    if 'is_admin' in data and isinstance(data['is_admin'], bool):
        user_to_update.is_admin = data['is_admin']
    else:
        return jsonify({"msg": "Invalid request. 'is_admin' field must be a boolean."}), 400
    
    db.session.commit()
    return jsonify(UserSchema.from_orm(user_to_update).model_dump())

@admin_bp.route('/apikeys', methods=['GET'])
@jwt_required() # Any logged in user can manage their own keys
def get_api_keys():
    user_id = get_jwt_identity()
    keys = crud.get_api_keys_for_user(db, user_id)
    # Don't send the hash to the client
    return jsonify([
        {
            "id": key.id,
            "name": key.name,
            "key_prefix": key.key_prefix,
            "created_at": key.created_at.isoformat(),
            "last_used": key.last_used.isoformat() if key.last_used else None,
            "is_active": key.is_active
        } for key in keys
    ])

@admin_bp.route('/apikeys', methods=['POST'])
@jwt_required()
def create_api_key():
    user_id = get_jwt_identity()
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"error": "A name for the key is required."}), 422
    
    db_key, raw_key = crud.create_api_key(db, user_id, name)
    # This is the ONLY time the user will see the full key
    return jsonify({
        "message": "API Key created successfully. Store it securely, you will not see it again.",
        "name": db_key.name,
        "key_prefix": db_key.key_prefix,
        "raw_key": raw_key
    }), 201

@admin_bp.route('/apikeys/<int:key_id>', methods=['DELETE'])
@jwt_required()
def delete_api_key(key_id):
    user_id = get_jwt_identity()
    success = crud.delete_api_key(db, key_id, user_id)
    if not success:
        return jsonify({"error": "API Key not found or you are not authorized to delete it."}), 404
    return '', 204
# --- END OF FILE app/routes/admin_routes.py ---
