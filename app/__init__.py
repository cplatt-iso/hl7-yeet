# --- START OF FILE app/__init__.py ---

import os
import logging
from flask import Flask
from dotenv import load_dotenv
from .commands import register_commands

# Fucking monkey patch first, always.
import eventlet
eventlet.monkey_patch()

# --- STEP 1: Import extensions from our extensions.py file ---
from .extensions import db, cors, socketio, bcrypt, jwt

# --- STEP 2: Import Blueprints ---
from .routes.auth_routes import auth_bp
from .routes.mllp_routes import mllp_bp
from .routes.util_routes import util_bp

# Import models so that create_all knows about them
from . import models

def create_app():
    """
    The holy application factory. Creates and configures the Flask app.
    This is the way.
    """
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    logging.info("HL7 Yeeter Backend: Initializing application factory...")

    app = Flask(__name__)
    
    # --- Configuration from Environment Variables ---
    # THIS IS THE ONE TRUE WAY FOR THIS PROJECT
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
    # JWT_ACCESS_TOKEN_EXPIRES must be an integer (seconds)
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 24)) * 3600

    # --- Initialize Extensions with the App ---
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    socketio.init_app(app, cors_allowed_origins="*")
    bcrypt.init_app(app)
    jwt.init_app(app)

    # --- Register Blueprints ---
    logging.info("Registering blueprints...")
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(mllp_bp, url_prefix='/api')
    app.register_blueprint(util_bp, url_prefix='/api')
    
    # --- Create Database Tables ---
    with app.app_context():
        logging.info("Initializing database tables from models...")
        db.create_all()
        logging.info("Database tables checked/created successfully.")

    register_commands(app)

    logging.info("HL7 Yeeter Backend: Application creation complete.")
    return app
# --- END OF FILE app/__init__.py ---