# --- START OF FILE run.py ---
import logging
from app import create_app, socketio

# Create the Flask app instance using our factory
app = create_app()

if __name__ == '__main__':
    logging.info("Starting Flask-SocketIO server with eventlet...")
    # use_reloader=False is important for eventlet
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)
# --- END OF FILE run.py ---