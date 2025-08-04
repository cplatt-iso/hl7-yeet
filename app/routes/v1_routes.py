# --- CREATE NEW FILE: app/routes/v1_routes.py ---

import functools
from flask import Blueprint, jsonify, request, current_app
from .. import crud, schemas, models
from ..extensions import db, socketio, bcrypt
from ..util.simulation_runner import run_simulation_task

v1_bp = Blueprint('v1_api', __name__, url_prefix='/api/v1')

def api_key_required(f):
    """Custom decorator to protect routes with an API key."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authorization header is missing or invalid."}), 401
        
        raw_key = auth_header.split(' ')[1]
        if not raw_key.startswith('ytr_'):
            return jsonify({"error": "Invalid API key format."}), 401

        key_prefix = raw_key[:8]
        api_key_obj = crud.get_api_key_by_prefix(db, key_prefix)

        if not api_key_obj or not api_key_obj.is_active:
            return jsonify({"error": "API key is invalid or inactive."}), 403

        if not bcrypt.check_password_hash(api_key_obj.key_hash, raw_key):
            return jsonify({"error": "API key is invalid."}), 403
        
        # Key is valid, update last_used and proceed
        crud.update_api_key_last_used(db, key_prefix)
        
        return f(api_key_obj.user, *args, **kwargs)
    return decorated_function

@v1_bp.route('/runs/<int:template_id>', methods=['POST'])
@api_key_required
def run_simulation_via_api(user: models.User, template_id: int):
    """Triggers a simulation run via an API key."""
    try:
        data = request.get_json() if request.is_json else {}
        patient_count = int(data.get('patient_count', 1))
        if patient_count <= 0:
             return jsonify({"error": "patient_count must be a positive integer."}), 422
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid patient_count provided."}), 422

    template = crud.get_simulation_template_by_id(db, template_id)
    if not template or template.user_id != user.id:
        # We don't distinguish between not found and unauthorized for security
        return jsonify({"error": "Simulation template not found or you are not authorized to use it."}), 404

    new_run = crud.create_simulation_run(db, user_id=user.id, template_id=template.id, patient_count=patient_count)
    
    app_context = current_app.app_context
    socketio.start_background_task(run_simulation_task, run_id=new_run.id, app_context=app_context)

    return jsonify({
        "message": "Simulation run initiated successfully.", 
        "run_id": new_run.id,
        "template_id": template.id,
        "patient_count": new_run.patient_count,
        "status_url": f"/api/simulator/runs/{new_run.id}" # Inform user where to check status
    }), 202