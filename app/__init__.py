# --- START OF FILE app/__init__.py ---

import os
import logging
from flask import Flask, request
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
from .routes.system_routes import system_bp

from . import models as _models  # noqa: F401 - imported for SQLAlchemy model registration
from . import crud  # noqa: F401



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
    socketio.init_app(app, 
                     cors_allowed_origins="*",
                     logger=True,
                     engineio_logger=True,
                     ping_timeout=60,
                     ping_interval=25,
                     allow_upgrades=True)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # --- User Loader for JWT ---
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return crud.get_user_by_id(db, int(identity))
        
    # --- NEW: SOCKET.IO HANDLERS FOR SIMULATOR LOGGING ---
    @socketio.on('connect')
    def handle_connect(auth=None):
        """Handle Socket.IO client connection with optional authentication."""
        try:
            # Try to authenticate if token is provided
            token = None
            if auth and 'token' in auth:
                token = auth['token']
            elif request.args.get('token'):
                token = request.args.get('token')
            
            if token:
                try:
                    # Validate JWT token
                    from flask_jwt_extended import decode_token
                    decoded = decode_token(token)
                    user_id = decoded['sub']
                    user = crud.get_user_by_id(db, int(user_id))
                    if user:
                        logging.info(f"Socket.IO: Authenticated user {user.username} connected")
                    else:
                        logging.warning(f"Socket.IO: Invalid user ID {user_id} in token")
                except Exception as e:
                    logging.warning(f"Socket.IO: Token validation failed: {e}")
            else:
                logging.info("Socket.IO: Anonymous client connected (no token provided)")
            
            logging.info("Socket.IO: Client connected successfully")
        
        except Exception as e:
            logging.error(f"Socket.IO: Connection error: {e}")

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle Socket.IO client disconnection."""
        logging.info("Socket.IO: Client disconnected")

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
    app.register_blueprint(system_bp)  # Health check endpoint
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(mllp_bp, url_prefix='/api')
    app.register_blueprint(util_bp, url_prefix='/api')    
    app.register_blueprint(admin_bp, url_prefix='/api/admin')        
    app.register_blueprint(listener_bp)     
    app.register_blueprint(endpoint_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(v1_bp)
    
    # Import and register SSE routes
    from .routes.sse_routes import sse_bp
    app.register_blueprint(sse_bp)


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