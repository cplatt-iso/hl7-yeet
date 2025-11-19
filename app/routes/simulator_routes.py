# --- START OF FILE app/routes/simulator_routes.py ---

# ... (imports and other routes are unchanged) ...
from typing import Any, Dict, cast

from flask import Blueprint, jsonify, request, current_app
from pydantic import ValidationError

from .. import crud, schemas
from ..catalog.factory import get_exam_factory
from ..extensions import db, socketio
from ..routes.admin_routes import admin_required
from ..util.simulation_runner import run_simulation_task
from ..auth_utils import auth_required, get_authenticated_user, get_authenticated_user_id

simulator_bp = Blueprint('simulator', __name__, url_prefix='/api/simulator')


def _serialize_exam_spec(exam: Any) -> Dict[str, Any]:
    model_dump = getattr(exam, "model_dump", None)
    if callable(model_dump):
        return cast(Dict[str, Any], model_dump(mode='json'))
    dict_method = getattr(exam, "dict", None)
    if callable(dict_method):
        return cast(Dict[str, Any], dict_method())
    raise TypeError("ExamSpec object could not be serialized")


def _build_factory_filters(filter_model: schemas.ExamFilterParams) -> dict:
    filters = {
        'modality': filter_model.modality,
        'body_part': filter_model.body_part,
        'setting': filter_model.setting,
        'laterality': filter_model.laterality,
        'patient_age': filter_model.patient_age,
        'patient_sex': filter_model.patient_sex,
    }
    return {key: value for key, value in filters.items() if value not in (None, '')}


@simulator_bp.route('/exams', methods=['GET'])
@auth_required()
def list_exam_specs():
    raw_query = dict(request.args.items())
    try:
        filters_model = schemas.ExamFilterParams.model_validate(raw_query)
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    filter_kwargs = _build_factory_filters(filters_model)
    factory = get_exam_factory()
    exams = factory.list_exams(**filter_kwargs)
    payload = [_serialize_exam_spec(exam) for exam in exams]
    response = {
        'metadata': factory.get_catalog_metadata(),
        'count': len(payload),
        'filters': filter_kwargs,
        'exams': payload,
    }
    return jsonify(response)


@simulator_bp.route('/exams/<string:exam_id>', methods=['GET'])
@auth_required()
def get_exam_spec(exam_id: str):
    factory = get_exam_factory()
    try:
        exam = factory.get_exam_by_id(exam_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(_serialize_exam_spec(exam))


@simulator_bp.route('/exams/modalities', methods=['GET'])
@auth_required()
def list_exam_modalities():
    factory = get_exam_factory()
    modalities = [
        {
            'code': code,
            'count': len(factory.get_exams_by_modality(code)),
        }
        for code in factory.get_available_modalities()
    ]
    return jsonify({'modalities': modalities})


@simulator_bp.route('/exams/select', methods=['POST'])
@auth_required()
def select_exam_spec():
    try:
        selection = schemas.ExamSelectionRequest.model_validate(request.get_json() or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 422

    factory = get_exam_factory()
    filter_kwargs = _build_factory_filters(selection)
    strategy = 'random'

    try:
        if selection.exam_id:
            exam = factory.get_exam_by_id(selection.exam_id)
            strategy = 'exam_id'
        elif selection.cpt_code:
            exam = factory.get_exam_by_cpt_code(selection.cpt_code)
            strategy = 'cpt_code'
        else:
            exam = factory.get_random_exam(**filter_kwargs)
            strategy = 'random'
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    payload = _serialize_exam_spec(exam)
    payload['_selection'] = {
        'strategy': strategy,
        'filters': filter_kwargs,
    }
    return jsonify(payload)

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
    summaries = [
        schemas.SimulationRunSummaryResponse.model_validate(run).model_dump()
        for run in runs
    ]
    return jsonify(summaries)

@simulator_bp.route('/runs/<int:run_id>', methods=['GET'])
@auth_required()
def get_run_details(run_id):
    user_id = get_authenticated_user_id()
    default_limit = current_app.config.get('SIM_RUN_EVENTS_DEFAULT_LIMIT', 2000)
    events_limit = request.args.get('events_limit', type=int) or default_limit
    events_offset = request.args.get('events_offset', type=int) or 0
    events_order = request.args.get('events_order', default='desc')

    events_limit = max(events_limit, 1)
    events_offset = max(events_offset, 0)
    events_order_normalized = (events_order or 'desc').lower()
    if events_order_normalized not in {'asc', 'desc'}:
        events_order_normalized = 'desc'

    run = crud.get_simulation_run_by_id(db, run_id, with_events=False)
    if not run or (not get_authenticated_user().is_admin and run.user_id != user_id):
        return jsonify({"error": "Simulation run not found or unauthorized"}), 404

    events, total_events = crud.get_simulation_run_events(
        db,
        run_id,
        limit=events_limit,
        offset=events_offset,
        order=events_order_normalized,
    )

    run.events = events
    run_payload = schemas.SimulationRunResponse.model_validate(run).model_dump()

    returned_count = len(events)
    remaining_count = max(total_events - (events_offset + returned_count), 0)

    run_payload.update({
        'events_limit': events_limit,
        'events_offset': events_offset,
        'events_order': events_order_normalized,
        'events_total': total_events,
        'events_returned': returned_count,
        'events_remaining': remaining_count,
        'events_truncated': remaining_count > 0 or events_offset > 0,
    })

    return jsonify(run_payload)


@simulator_bp.route('/runs/<int:run_id>/stats', methods=['GET'])
@auth_required()
def get_run_stats(run_id):
    user_id = get_authenticated_user_id()
    run = crud.get_simulation_run_by_id(db, run_id, with_events=True)
    if not run or (not get_authenticated_user().is_admin and run.user_id != user_id):
        return jsonify({"error": "Simulation run not found or unauthorized"}), 404

    stats_payload = crud.calculate_simulation_run_stats(run)
    stats_response = schemas.SimulationRunStatsResponse.model_validate(stats_payload)
    return jsonify(stats_response.model_dump(mode='json'))


@simulator_bp.route('/runs/<int:run_id>/metrics', methods=['GET'])
@auth_required()
def get_run_metrics(run_id):
    user_id = get_authenticated_user_id()
    run = crud.get_simulation_run_by_id(db, run_id, with_events=False)
    if not run or (not get_authenticated_user().is_admin and run.user_id != user_id):
        return jsonify({"error": "Simulation run not found or unauthorized"}), 404

    stats_record = crud.get_run_stats_record(db, run_id, create_if_missing=True)
    if not stats_record:
        return jsonify({"error": "Metrics not available"}), 404

    default_jobs_limit = current_app.config.get('SIM_RUN_WORKER_JOBS_DEFAULT_LIMIT', 500)
    max_jobs_limit = current_app.config.get('SIM_RUN_WORKER_JOBS_MAX_LIMIT', max(default_jobs_limit, 2000))

    jobs_limit = request.args.get('jobs_limit', type=int) or default_jobs_limit
    jobs_offset = request.args.get('jobs_offset', type=int) or 0
    jobs_order = request.args.get('jobs_order', default='desc') or 'desc'

    jobs_limit = max(1, min(jobs_limit, max_jobs_limit))
    jobs_offset = max(jobs_offset, 0)
    jobs_order_normalized = jobs_order.lower()
    if jobs_order_normalized not in {'asc', 'desc'}:
        jobs_order_normalized = 'desc'

    metrics_payload = crud.build_run_metrics_payload(
        stats_record,
        run=run,
        user=getattr(run, 'user', None),
        template=getattr(run, 'template', None),
    )

    metrics_response = schemas.SimulationRunMetricsResponse.model_validate(metrics_payload)
    worker_metrics, total_worker_metrics = crud.get_worker_metrics_for_run(
        db,
        run_id,
        limit=jobs_limit,
        offset=jobs_offset,
        order=jobs_order_normalized,
    )
    worker_payload = [
        schemas.WorkerJobMetricResponse.model_validate(metric).model_dump(mode='json')
        for metric in worker_metrics
    ]

    response = metrics_response.model_dump(mode='json')
    returned_count = len(worker_payload)
    remaining_count = max(total_worker_metrics - (jobs_offset + returned_count), 0)

    response.update({
        'worker_jobs': worker_payload,
        'worker_jobs_limit': jobs_limit,
        'worker_jobs_offset': jobs_offset,
        'worker_jobs_order': jobs_order_normalized,
        'worker_jobs_total': total_worker_metrics,
        'worker_jobs_returned': returned_count,
        'worker_jobs_remaining': remaining_count,
        'worker_jobs_truncated': remaining_count > 0 or jobs_offset > 0,
    })
    return jsonify(response)


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