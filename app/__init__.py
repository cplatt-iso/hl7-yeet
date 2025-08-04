# --- START OF FILE app/__init__.py ---

import os
import logging
from flask import Flask
from flask_jwt_extended import get_current_user # I'm adding this back just in case, it's good practice
from dotenv import load_dotenv
from .commands import register_commands
from werkzeug.middleware.proxy_fix import ProxyFix

if not os.environ.get("FLASK_SKIP_EVENTLET"):
    import eventlet
    eventlet.monkey_patch()

# --- MODIFICATION: Import flask_socketio functions for room management ---
from .extensions import db, cors, socketio, bcrypt, jwt
from flask_socketio import join_room, leave_room

# --- Import Blueprints ---
from .routes.v1_routes import v1_bp
from .routes.auth_routes import auth_bp
from .routes.mllp_routes import mllp_bp
from .routes.util_routes import util_bp
from .routes.admin_routes import admin_bp
from .routes.listener_routes import listener_bp
from .routes.simulator_routes import simulator_bp
from .routes.endpoint_routes import endpoint_bp

from . import models, crud



def create_app():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    logging.info("HL7 Yeeter Backend: Initializing application factory...")

    app = Flask(__name__)

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
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    socketio.init_app(app, cors_allowed_origins="*")
    bcrypt.init_app(app)
    jwt.init_app(app)

    # --- User Loader for JWT ---
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return crud.get_user_by_id(db, int(identity))
        
    # --- NEW: SOCKET.IO HANDLERS FOR SIMULATOR LOGGING ---
    @socketio.on('join_run_room')
    def handle_join_run_room(data):
        run_id = data.get('run_id')
        if run_id:
            join_room(f'run-{run_id}')
            logging.info(f"Socket client joined room: run-{run_id}")

    @socketio.on('leave_run_room')
    def handle_leave_run_room(data):
        run_id = data.get('run_id')
        if run_id:
            leave_room(f'run-{run_id}')
            logging.info(f"Socket client left room: run-{run_id}")


    # --- Register Blueprints ---
    logging.info("Registering blueprints...")
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(mllp_bp, url_prefix='/api')
    app.register_blueprint(util_bp, url_prefix='/api')    
    app.register_blueprint(admin_bp, url_prefix='/api/admin')        
    app.register_blueprint(listener_bp)     
    app.register_blueprint(endpoint_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(v1_bp)


    # --- Create/Update Database Tables ---
    with app.app_context():
        logging.info("Initializing database tables from models...")
        # This will now automatically create all our new simulator tables
        db.create_all()
        logging.info("Database tables checked/created successfully.")

    register_commands(app)

    logging.info("HL7 Yeeter Backend: Application creation complete.")
    return app

# --- END OF FILE app/__init__.py ---