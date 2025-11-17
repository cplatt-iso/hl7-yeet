# --- NEW FILE: app/routes/sse_routes.py ---
"""Server-Sent Events routes for real-time streaming."""
from flask import Blueprint, Response, current_app, request
from flask_jwt_extended import decode_token
import json
import time
import logging
from ..extensions import db
from .. import crud
from ..auth_utils import validate_api_key

sse_bp = Blueprint('sse', __name__, url_prefix='/api/sse')

# Store active SSE connections by run_id
active_connections = {}

@sse_bp.route('/run/<int:run_id>')
def stream_run_logs(run_id):
    """Stream simulation run logs via Server-Sent Events."""
    # Get token from query parameter since EventSource doesn't support headers
    token = request.args.get('token')
    if not token:
        return Response("Missing token parameter", status=401)
    
    user = None
    if token.startswith("ytr_"):
        user, _ = validate_api_key(token)
        if not user:
            logging.warning("SSE rejected invalid API key token")
            return Response("Invalid token", status=401)
    else:
        try:
            decoded_token = decode_token(token)
            user_id = int(decoded_token['sub'])
            user = crud.get_user_by_id(db, user_id)
            if not user:
                logging.warning("SSE rejected unknown JWT subject %s", decoded_token['sub'])
                return Response("Invalid token", status=401)
        except Exception as e:  # pragma: no cover - defensive logging
            logging.error(f"SSE auth error: {e}")
            return Response("Invalid token", status=401)
    
    def generate():
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connection', 'message': 'Connected to run stream'})}\n\n"
        
        # Verify the run exists and belongs to user (optional security check)
        run = crud.get_simulation_run_by_id(db, run_id, with_events=False)
        if not run:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Run not found'})}\n\n"
            return
        if run.user_id != user.id and not getattr(user, "is_admin", False):
            yield f"data: {json.dumps({'type': 'error', 'message': 'Unauthorized'})}\n\n"
            return
            
        page_size = current_app.config.get('SIM_RUN_EVENTS_DEFAULT_LIMIT', 2000)
        if page_size <= 0:
            page_size = 500

        events_offset = 0
        last_event_id = 0

        while True:
            events_batch, total_events = crud.get_simulation_run_events(
                db,
                run_id,
                limit=page_size,
                offset=events_offset,
                order='asc',
            )

            if not events_batch:
                break

            for event in events_batch:
                event_data = {
                    'type': 'log_update',
                    'run_id': run_id,
                    'event': {
                        'id': event.id,
                        'timestamp': event.timestamp.isoformat(),
                        'step_order': event.step_order,
                        'iteration': event.iteration,
                        'status': event.status,
                        'details': event.details
                    }
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                last_event_id = event.id

            events_offset += len(events_batch)
            if events_offset >= total_events:
                break

        if run_id not in active_connections:
            active_connections[run_id] = []
        active_connections[run_id].append(generate)
        
        while True:
            try:
                # Check for new events
                with db.session.no_autoflush:
                    new_events = db.session.query(crud.models.SimulationRunEvent).filter(
                        crud.models.SimulationRunEvent.run_id == run_id,
                        crud.models.SimulationRunEvent.id > last_event_id
                    ).order_by(crud.models.SimulationRunEvent.id).limit(page_size).all()
                    
                    for event in new_events:
                        event_data = {
                            'type': 'log_update',
                            'run_id': run_id,
                            'event': {
                                'id': event.id,
                                'timestamp': event.timestamp.isoformat(),
                                'step_order': event.step_order,
                                'iteration': event.iteration,
                                'status': event.status,
                                'details': event.details
                            }
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                        last_event_id = event.id
                        
                    # Check if run is completed
                    run = crud.get_simulation_run_by_id(db, run_id, with_events=False)
                    if run and run.status in ['COMPLETED', 'ERROR']:
                        yield f"data: {json.dumps({'type': 'status_update', 'run_id': run_id, 'status': run.status})}\n\n"
                        if run.status == 'COMPLETED':
                            break
                            
                # Send heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logging.error(f"SSE stream error for run {run_id}: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
                
        # Clean up connection
        if run_id in active_connections:
            try:
                active_connections[run_id].remove(generate)
                if not active_connections[run_id]:
                    del active_connections[run_id]
            except ValueError:
                pass
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )

def broadcast_event_to_sse(run_id, event_data):
    """Broadcast an event to all SSE connections for a run."""
    # This is called from the simulation runner to push events
    # The SSE connections will pick up events via database polling
    # We could optimize this later with a proper event queue
    pass

def broadcast_status_to_sse(run_id, status):
    """Broadcast a status update to all SSE connections for a run."""
    # Similar to broadcast_event_to_sse, handled via polling for now
    pass
