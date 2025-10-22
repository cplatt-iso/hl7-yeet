# --- START OF FILE app/routes/system_routes.py ---
from flask import Blueprint, jsonify
from sqlalchemy import text
from app.database import db

system_bp = Blueprint('system', __name__, url_prefix='/api')

@system_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Kubernetes liveness/readiness probes.
    Checks database connectivity.
    """
    try:
        # Check database connection
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 503
