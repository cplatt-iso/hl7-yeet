# --- START OF FILE app/__init__.py ---

import os
import logging
from flask import Flask
from dotenv import load_dotenv
from .commands import register_commands
from werkzeug.middleware.proxy_fix import ProxyFix

if not os.environ.get("FLASK_SKIP_EVENTLET"):
    import eventlet
    eventlet.monkey_patch()

from .extensions import db, cors, socketio, bcrypt, jwt
# from flask_migrate import Migrate

# --- Import Blueprints ---
from .routes.auth_routes import auth_bp
from .routes.mllp_routes import mllp_bp
from .routes.util_routes import util_bp
from .routes.destination_routes import destinations_bp
from .routes.admin_routes import admin_bp
# --- NEW: Import the listener API blueprint ---
from .routes.listener_routes import listener_bp


from . import models

def create_app():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    logging.info("HL7 Yeeter Backend: Initializing application factory...")

    app = Flask(__name__)

    # Add ProxyFix middleware to handle X-Forwarded-Proto headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # --- Configuration ---
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 24)) * 3600
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max upload size

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --- Initialize Extensions ---
    db.init_app(app)
    # migrate = Migrate(app, db)  # Initialize Flask-Migrate
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    socketio.init_app(app, cors_allowed_origins="*")
    bcrypt.init_app(app)
    jwt.init_app(app)

    # --- Register Blueprints ---
    logging.info("Registering blueprints...")
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(mllp_bp, url_prefix='/api')
    app.register_blueprint(util_bp, url_prefix='/api')
    app.register_blueprint(destinations_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')    
    app.register_blueprint(listener_bp)


    # --- Create/Update Database Tables ---
    with app.app_context():
        logging.info("Initializing database tables from models...")
        # This will now automatically create the `received_messages` table for you
        # because you added the model to app/models.py
        db.create_all()
        logging.info("Database tables checked/created successfully.")

    register_commands(app)

    logging.info("HL7 Yeeter Backend: Application creation complete.")
    return app

# --- END OF FILE app/__init__.py ---