# --- START OF FILE app/extensions.py ---
"""
This module initializes the extensions used by the Flask application.
By instantiating them here, we can import them into other modules
(like blueprints) without running into circular import errors.

The extensions are configured within the application factory in __init__.py.
"""
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

# Instantiate the extensions
db = SQLAlchemy()
cors = CORS()
socketio = SocketIO(async_mode='eventlet')
bcrypt = Bcrypt()
jwt = JWTManager()
# --- END OF FILE app/extensions.py ---