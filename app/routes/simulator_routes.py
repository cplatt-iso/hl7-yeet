# --- START OF FILE app/routes/simulator_routes.py ---

# ... (imports and other routes are unchanged) ...
from flask import Blueprint, jsonify, request, current_app
from pydantic import ValidationError

from .. import crud, schemas
from ..extensions import db, socketio
from ..routes.admin_routes import admin_required
from ..util.simulation_runner import run_simulation_task
from ..auth_utils import auth_required, get_authenticated_user, get_authenticated_user_id

simulator_bp = Blueprint('simulator', __name__, url_prefix='/api/simulator')

# ... (Generator and Simulation Template CRUDs are unchanged) ...
# --- Generator Template CRUD ---
@simulator_bp.route('/generators', methods=['POST'])
@admin_required()
def create_generator_template():
    user_id = get_authenticated_user_id()
    try:
        data = schemas.GeneratorTemplateCreate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422
    template = crud.create_generator_template(db, user_id=user_id, template_data=data)
    return jsonify(schemas.GeneratorTemplateResponse.model_validate(template).model_dump()), 201

@simulator_bp.route('/generators', methods=['GET'])
@auth_required()
def get_all_generator_templates():
    templates = crud.get_all_generator_templates(db)
    return jsonify([schemas.GeneratorTemplateResponse.model_validate(t).model_dump() for t in templates])

@simulator_bp.route('/generators/<int:template_id>', methods=['PUT'])
@admin_required()
def update_generator_template(template_id):
    try:
        data = schemas.GeneratorTemplateCreate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422
    template = crud.update_generator_template(db, template_id=template_id, update_data=data)
    if not template:
        return jsonify({"error": "Generator template not found"}), 404
    return jsonify(schemas.GeneratorTemplateResponse.model_validate(template).model_dump())

@simulator_bp.route('/generators/<int:template_id>', methods=['DELETE'])
@admin_required()
def delete_generator_template(template_id):
    success = crud.delete_generator_template(db, template_id=template_id)
    if not success:
        return jsonify({"error": "Generator template not found"}), 404
    return '', 204

# --- Simulation Template (Workflow) CRUD ---
@simulator_bp.route('/templates', methods=['POST'])
@auth_required()
def create_simulation_template():
    user_id = get_authenticated_user_id()
    try:
        data = schemas.SimulationTemplateCreate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422
    template = crud.create_simulation_template(db, user_id=user_id, template_data=data)
    return jsonify(schemas.SimulationTemplateResponse.model_validate(template).model_dump()), 201

@simulator_bp.route('/templates', methods=['GET'])
@auth_required()
def get_user_simulation_templates():
    user_id = get_authenticated_user_id()
    templates = crud.get_simulation_templates_for_user(db, user_id=user_id)
    return jsonify([schemas.SimulationTemplateResponse.model_validate(t).model_dump() for t in templates])
    
@simulator_bp.route('/templates/<int:template_id>', methods=['GET'])
@auth_required()
def get_simulation_template(template_id):
    user_id = get_authenticated_user_id()
    template = crud.get_simulation_template_by_id(db, template_id)
    if not template or (not get_authenticated_user().is_admin and template.user_id != user_id):
         return jsonify({"error": "Template not found or unauthorized"}), 404
    return jsonify(schemas.SimulationTemplateResponse.model_validate(template).model_dump())

@simulator_bp.route('/templates/<int:template_id>', methods=['PUT'])
@auth_required()
def update_simulation_template(template_id):
    user_id = get_authenticated_user_id()
    try:
        data = schemas.SimulationTemplateUpdate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422
    template = crud.update_simulation_template(db, template_id, user_id, get_authenticated_user().is_admin, data)
    if not template:
        return jsonify({"error": "Template not found or unauthorized"}), 404
    return jsonify(schemas.SimulationTemplateResponse.model_validate(template).model_dump())

@simulator_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@auth_required()
def delete_simulation_template(template_id):
    user_id = get_authenticated_user_id()
    success = crud.delete_simulation_template(db, template_id, user_id, get_authenticated_user().is_admin)
    if not success:
        return jsonify({"error": "Template not found or unauthorized"}), 404
    return '', 204
# --- Simulation Run Endpoints ---

@simulator_bp.route('/run', methods=['POST'])
@auth_required()
def run_simulation():
    user_id = get_authenticated_user_id()
    try:
        # --- MODIFICATION: Use the updated schema directly ---
        data = schemas.SimulationRunCreate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422

    template = crud.get_simulation_template_by_id(db, data.template_id)
    if not template or (not get_authenticated_user().is_admin and template.user_id != int(user_id)):
        return jsonify({"error": "Simulation template not found or unauthorized."}), 404

    # Now this call will work perfectly
    new_run = crud.create_simulation_run(db, user_id=user_id, template_id=data.template_id, patient_count=data.patient_count)
    
    app_context = current_app.app_context
    socketio.start_background_task(run_simulation_task, run_id=new_run.id, app_context=app_context)

    return jsonify({"message": "Simulation run initiated successfully.", "run_id": new_run.id}), 202

# --- NEW: Endpoints for fetching run history ---
@simulator_bp.route('/runs', methods=['GET'])
@auth_required()
def get_runs_history():
    user_id = get_authenticated_user_id()
    runs = crud.get_simulation_runs_for_user(db, user_id=user_id)
    return jsonify([schemas.SimulationRunResponse.model_validate(r).model_dump(exclude={'events'}) for r in runs])

@simulator_bp.route('/runs/<int:run_id>', methods=['GET'])
@auth_required()
def get_run_details(run_id):
    user_id = get_authenticated_user_id()
    run = crud.get_simulation_run_by_id(db, run_id)
    if not run or (not get_authenticated_user().is_admin and run.user_id != user_id):
        return jsonify({"error": "Simulation run not found or unauthorized"}), 404
    return jsonify(schemas.SimulationRunResponse.model_validate(run).model_dump())


@simulator_bp.route('/runs/<int:run_id>/stats', methods=['GET'])
@auth_required()
def get_run_stats(run_id):
    user_id = get_authenticated_user_id()
    run = crud.get_simulation_run_by_id(db, run_id)
    if not run or (not get_authenticated_user().is_admin and run.user_id != user_id):
        return jsonify({"error": "Simulation run not found or unauthorized"}), 404

    stats_payload = crud.calculate_simulation_run_stats(run)
    stats_response = schemas.SimulationRunStatsResponse.model_validate(stats_payload)
    return jsonify(stats_response.model_dump(mode='json'))


@simulator_bp.route('/runs/<int:run_id>/cancel', methods=['POST'])
@auth_required()
def cancel_run(run_id):
    user_id = get_authenticated_user_id()
    run, error = crud.request_simulation_run_cancel(db, run_id, user_id, get_authenticated_user().is_admin)
    if run is None:
        if error == "Run not found":
            return jsonify({"error": "Simulation run not found"}), 404
        if error == "Unauthorized":
            return jsonify({"error": "You are not authorized to cancel this run."}), 403
        return jsonify({"error": error or "Unable to cancel simulation run."}), 400

    if error == "Run is already finished":
        return jsonify({"error": "Simulation run is already finished."}), 409

    socketio.emit('sim_run_status_update', {'run_id': run.id, 'status': 'CANCELLED'}, to=f'run-{run.id}')
    return jsonify({"message": "Cancellation requested.", "run_id": run.id}), 202

@simulator_bp.route('/runs/<int:run_id>', methods=['DELETE'])
@auth_required()
def delete_run(run_id):
    user_id = get_authenticated_user_id()
    success = crud.delete_simulation_run(db, run_id, user_id, get_authenticated_user().is_admin)
    if not success:
        return jsonify({"error": "Simulation run not found or you're not authorized to delete it."}), 404
    return '', 204

@simulator_bp.route('/runs', methods=['DELETE'])
@auth_required()
def delete_all_runs():
    user_id = get_authenticated_user_id()
    crud.delete_all_simulation_runs_for_user(db, user_id=user_id)
    return '', 204
# --- END OF FILE app/routes/simulator_routes.py ---