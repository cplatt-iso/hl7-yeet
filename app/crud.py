# --- REPLACE app/crud.py ---

from sqlalchemy.orm import joinedload
from sqlalchemy import func, select, or_
from flask_sqlalchemy import SQLAlchemy
import logging 
from typing import Any

from . import models, schemas
from .extensions import bcrypt
from datetime import datetime
import secrets

# --- User CRUD (unchanged) ---

def get_user_by_id(db: SQLAlchemy, user_id: int) -> models.User | None:
    return db.session.get(models.User, user_id)

def get_user_by_username(db: SQLAlchemy, username: str) -> models.User | None:
    return db.session.execute(db.select(models.User).filter(func.lower(models.User.username) == func.lower(username))).scalar_one_or_none()

def get_user_by_email(db: SQLAlchemy, email: str) -> models.User | None:
    return db.session.execute(db.select(models.User).filter(func.lower(models.User.email) == func.lower(email))).scalar_one_or_none()

def get_user_by_google_id(db: SQLAlchemy, google_id: str) -> models.User | None:
    return db.session.execute(db.select(models.User).filter(models.User.google_id == google_id)).scalar_one_or_none()

def create_user(db: SQLAlchemy, user: schemas.UserCreate) -> models.User:
    user_count = db.session.execute(select(func.count(models.User.id))).scalar()
    is_first_user = (user_count == 0)
    hashed_password = bcrypt.generate_password_hash(user.password).decode('utf-8')
    db_user = models.User(username=user.username, email=user.email, password_hash=hashed_password, is_admin=is_first_user)
    db.session.add(db_user)
    db.session.commit()
    db.session.refresh(db_user)
    return db_user

def create_google_user(db: SQLAlchemy, email: str, username: str, google_id: str) -> models.User:
    user_count = db.session.execute(select(func.count(models.User.id))).scalar()
    is_first_user = (user_count == 0)
    placeholder_hash = bcrypt.generate_password_hash("!@#$Unusabl3P@ssw0rdForG00gl3Log!n#@$!").decode('utf-8')
    db_user = models.User(username=username, email=email, password_hash=placeholder_hash, google_id=google_id, is_admin=is_first_user)
    db.session.add(db_user)
    db.session.commit()
    db.session.refresh(db_user)
    return db_user

# --- Template CRUD (unchanged) ---

def get_templates_for_user(db: SQLAlchemy, user_id: int) -> list[models.UserTemplate]:
    return list(db.session.execute(db.select(models.UserTemplate).filter_by(user_id=user_id).order_by(models.UserTemplate.name)).scalars())

def create_template(db: SQLAlchemy, user_id: int, template: schemas.TemplateCreate) -> models.UserTemplate:
    db_template = models.UserTemplate(user_id=user_id, name=template.name, content=template.content)
    db.session.add(db_template)
    db.session.commit()
    db.session.refresh(db_template)
    return db_template

def delete_template(db: SQLAlchemy, user_id: int, template_id: int) -> models.UserTemplate | None:
    db_template = db.session.execute(db.select(models.UserTemplate).filter_by(id=template_id, user_id=user_id)).scalar_one_or_none()
    if db_template:
        db.session.delete(db_template)
        db.session.commit()
    return db_template

# --- Token Usage CRUD (unchanged) ---

def record_token_usage(db: SQLAlchemy, user_id: int, model_name: str, usage_data: dict) -> models.TokenUsage:
    db_usage = models.TokenUsage(user_id=user_id, model=model_name, input_tokens=usage_data.get('input_tokens', 0), output_tokens=usage_data.get('output_tokens', 0), total_tokens=usage_data.get('total_tokens', 0))
    db.session.add(db_usage)
    db.session.commit()
    db.session.refresh(db_usage)
    return db_usage

def get_total_usage_for_user(db: SQLAlchemy, user_id: int) -> int:
    total = db.session.scalar(db.select(func.sum(models.TokenUsage.total_tokens)).filter_by(user_id=user_id))
    return total or 0

def get_usage_by_model_for_user(db: SQLAlchemy, user_id: int) -> dict:
    results = db.session.execute(db.select(models.TokenUsage.model, func.sum(models.TokenUsage.total_tokens)).filter_by(user_id=user_id).group_by(models.TokenUsage.model)).all()
    return {model: total for model, total in results}

# --- Hl7Version CRUD (unchanged) ---

def get_all_hl7_versions(db: SQLAlchemy) -> list[models.Hl7Version]:
    return list(db.session.execute(
        db.select(models.Hl7Version)
        .options(joinedload(models.Hl7Version.user))
        .order_by(models.Hl7Version.version)
    ).scalars())

def get_active_hl7_versions(db: SQLAlchemy) -> list[models.Hl7Version]:
    return list(db.session.execute(
        db.select(models.Hl7Version).filter_by(is_active=True).order_by(models.Hl7Version.version.desc())
    ).scalars())

def get_hl7_version_by_id(db: SQLAlchemy, version_id: int) -> models.Hl7Version | None:
    return db.session.get(models.Hl7Version, version_id)

def toggle_hl7_version_status(db: SQLAlchemy, version_id: int) -> models.Hl7Version | None:
    version = get_hl7_version_by_id(db, version_id)
    if version:
        version.is_active = not version.is_active
        # If we are deactivating a default version, it can no longer be default.
        if not version.is_active and version.is_default:
            version.is_default = False
        db.session.commit()
        db.session.refresh(version)
    return version

def set_default_hl7_version(db: SQLAlchemy, version_id: int) -> models.Hl7Version | None:
    """Sets a specific version as the default, ensuring it's active and removing default from others."""
    new_default_version = get_hl7_version_by_id(db, version_id)
    
    # Can't set an inactive version as default
    if not new_default_version or not new_default_version.is_active:
        return None

    # Find the current default and unset it
    current_default = db.session.execute(
        db.select(models.Hl7Version).filter_by(is_default=True)
    ).scalar_one_or_none()

    if current_default and current_default.id != new_default_version.id:
        current_default.is_default = False

    # Set the new default
    new_default_version.is_default = True
    
    db.session.commit()
    db.session.refresh(new_default_version)
    
    return new_default_version

# --- Hl7TableDefinition CRUD (unchanged) ---

def get_distinct_table_ids(db: SQLAlchemy) -> list[str]:
    results = db.session.execute(
        select(models.Hl7TableDefinition.table_id).distinct().order_by(models.Hl7TableDefinition.table_id)
    ).scalars().all()
    return list(results)

def get_definitions_for_table(db: SQLAlchemy, table_id: str) -> list[models.Hl7TableDefinition]:
    return list(db.session.execute(
        db.select(models.Hl7TableDefinition).filter_by(table_id=table_id).order_by(models.Hl7TableDefinition.value)
    ).scalars())

def get_definition_by_id(db: SQLAlchemy, def_id: int) -> models.Hl7TableDefinition | None:
    return db.session.get(models.Hl7TableDefinition, def_id)

def create_definition(db: SQLAlchemy, definition: schemas.DefinitionCreate) -> models.Hl7TableDefinition:
    db_def = models.Hl7TableDefinition(
        table_id=definition.table_id,
        value=definition.value,
        description=definition.description
    )
    db.session.add(db_def)
    db.session.commit()
    db.session.refresh(db_def)
    return db_def

def update_definition(db: SQLAlchemy, def_id: int, definition_update: schemas.DefinitionUpdate) -> models.Hl7TableDefinition | None:
    db_def = get_definition_by_id(db, def_id)
    if db_def:
        update_data = definition_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_def, key, value)
        db.session.commit()
        db.session.refresh(db_def)
    return db_def

def delete_definition(db: SQLAlchemy, def_id: int) -> bool:
    db_def = get_definition_by_id(db, def_id)
    if db_def:
        db.session.delete(db_def)
        db.session.commit()
        return True
    return False

def clear_hl7_table_definitions(db: SQLAlchemy):
    db.session.query(models.Hl7TableDefinition).delete()
    db.session.commit()

def bulk_add_hl7_table_definitions(db: SQLAlchemy, definitions: list[dict]):
    db.session.bulk_insert_mappings(models.Hl7TableDefinition, definitions) # type: ignore
    db.session.commit()

# --- SystemMetadata CRUD (unchanged) ---

def get_metadata(db: SQLAlchemy, key: str) -> models.SystemMetadata | None:
    return db.session.get(models.SystemMetadata, key)

def set_metadata(db: SQLAlchemy, key: str, value: str):
    metadata_obj = get_metadata(db, key)
    if metadata_obj:
        metadata_obj.value = value
    else:
        metadata_obj = models.SystemMetadata(key=key, value=value)
        db.session.add(metadata_obj)
    db.session.commit()

def get_terminology_stats(db: SQLAlchemy) -> dict:
    table_count = db.session.execute(select(func.count(func.distinct(models.Hl7TableDefinition.table_id)))).scalar()
    definition_count = db.session.execute(select(func.count(models.Hl7TableDefinition.id))).scalar()
    last_updated_obj = get_metadata(db, 'terminology_last_updated')
    return {"table_count": table_count or 0, "definition_count": definition_count or 0, "last_updated": last_updated_obj.value if last_updated_obj else None}

# --- ReceivedMessage CRUD (unchanged) ---

def add_received_message(db: SQLAlchemy, raw_message: str) -> models.ReceivedMessage:
    message_type, control_id, sending_app = "Unknown", "Unknown", "Unknown"
    try:
        segments = raw_message.split('\r')
        msh_segment = next((s for s in segments if s.startswith('MSH')), None)
        if msh_segment:
            fields = msh_segment.split('|')
            sending_app = fields[2] if len(fields) > 2 else "Unknown"
            message_type = fields[8] if len(fields) > 8 else "Unknown"
            control_id = fields[9] if len(fields) > 9 else "Unknown"
    except Exception as e:
        logging.error(f"Failed to parse MSH for received message: {e}")

    db_message = models.ReceivedMessage(
        raw_message=raw_message,
        message_type=message_type,
        control_id=control_id,
        sending_app=sending_app
    )
    db.session.add(db_message)
    db.session.commit()
    db.session.refresh(db_message)
    return db_message

def get_received_messages(db: SQLAlchemy, page: int, per_page: int, search_term: str | None = None):
    query = db.select(models.ReceivedMessage)
    
    if search_term:
        st = f"%{search_term}%"
        query = query.filter(or_(
            models.ReceivedMessage.raw_message.ilike(st),
            models.ReceivedMessage.message_type.ilike(st),
            models.ReceivedMessage.sending_app.ilike(st),
            models.ReceivedMessage.control_id.ilike(st)
        ))

    query = query.order_by(models.ReceivedMessage.timestamp.desc())
    
    paginated_query = db.paginate(query, page=page, per_page=per_page, error_out=False)
    return paginated_query

def get_received_message_by_id(db: SQLAlchemy, message_id: int) -> models.ReceivedMessage | None:
    return db.session.get(models.ReceivedMessage, message_id)

def clear_all_received_messages(db: SQLAlchemy):
    db.session.query(models.ReceivedMessage).delete()
    db.session.commit()

# --- NEW SIMULATOR CRUDS ---

# --- Endpoint (Destination) CRUD ---
def create_endpoint(db: SQLAlchemy, user_id: int, endpoint_data: schemas.EndpointCreate) -> models.Endpoint:
    endpoint_dict = endpoint_data.model_dump()
    endpoint_dict['user_id'] = user_id
    db_endpoint = models.Endpoint(**endpoint_dict)
    db.session.add(db_endpoint)
    db.session.commit()
    db.session.refresh(db_endpoint)
    return db_endpoint

def get_endpoint_by_id(db: SQLAlchemy, endpoint_id: int) -> models.Endpoint | None:
    return db.session.get(models.Endpoint, endpoint_id)

def get_all_endpoints(db: SQLAlchemy) -> list[models.Endpoint]:
    return list(db.session.execute(db.select(models.Endpoint).order_by(models.Endpoint.name)).scalars())

def update_endpoint(db: SQLAlchemy, endpoint_id: int, update_data: schemas.EndpointUpdate) -> models.Endpoint | None:
    db_endpoint = get_endpoint_by_id(db, endpoint_id)
    if db_endpoint:
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(db_endpoint, key, value)
        db.session.commit()
        db.session.refresh(db_endpoint)
    return db_endpoint

def delete_endpoint(db: SQLAlchemy, endpoint_id: int) -> bool:
    db_endpoint = get_endpoint_by_id(db, endpoint_id)
    if db_endpoint:
        db.session.delete(db_endpoint)
        db.session.commit()
        return True
    return False

# --- Generator Template CRUD ---
def create_generator_template(db: SQLAlchemy, user_id: int, template_data: schemas.GeneratorTemplateCreate) -> models.GeneratorTemplate:
    db_template = models.GeneratorTemplate(**template_data.model_dump())
    db_template.user_id = user_id
    db.session.add(db_template)
    db.session.commit()
    db.session.refresh(db_template)
    return db_template

def get_generator_template_by_id(db: SQLAlchemy, template_id: int) -> models.GeneratorTemplate | None:
    return db.session.get(models.GeneratorTemplate, template_id)

def get_all_generator_templates(db: SQLAlchemy) -> list[models.GeneratorTemplate]:
    return list(db.session.execute(db.select(models.GeneratorTemplate).order_by(models.GeneratorTemplate.name)).scalars())

def update_generator_template(db: SQLAlchemy, template_id: int, update_data: schemas.GeneratorTemplateCreate) -> models.GeneratorTemplate | None:
    db_template = get_generator_template_by_id(db, template_id)
    if db_template:
        for key, value in update_data.model_dump().items():
            setattr(db_template, key, value)
        db.session.commit()
        db.session.refresh(db_template)
    return db_template

def delete_generator_template(db: SQLAlchemy, template_id: int) -> bool:
    db_template = get_generator_template_by_id(db, template_id)
    if db_template:
        db.session.delete(db_template)
        db.session.commit()
        return True
    return False

# --- Simulation Template CRUD ---
def create_simulation_template(db: SQLAlchemy, user_id: int, template_data: schemas.SimulationTemplateCreate) -> models.SimulationTemplate:
    """Creates a new simulation template with associated steps."""
    db_template = models.SimulationTemplate()
    db_template.user_id = user_id
    db_template.name = template_data.name
    db_template.description = template_data.description
    
    db.session.add(db_template)
    db.session.flush()  # Flush to get the template ID for the steps
    
    # Add steps
    for step_data in template_data.steps:
        db_step = models.SimulationStep(**step_data.model_dump())
        db_step.template_id = db_template.id
        db.session.add(db_step)
    
    db.session.commit()
    db.session.refresh(db_template)
    return db_template

def create_simulation_run(db: SQLAlchemy, user_id: int, template_id: int, patient_count: int) -> models.SimulationRun:
    """Creates a new record for a simulation run and returns it."""
    db_run = models.SimulationRun()
    db_run.user_id = user_id
    db_run.template_id = template_id
    db_run.patient_count = patient_count
    db_run.status = 'PENDING'
    db.session.add(db_run)
    db.session.commit()
    db.session.refresh(db_run)
    return db_run

def get_simulation_template_by_id(db: SQLAlchemy, template_id: int) -> models.SimulationTemplate | None:
    return db.session.query(models.SimulationTemplate).options(joinedload(models.SimulationTemplate.steps)).filter(models.SimulationTemplate.id == template_id).one_or_none()

def get_simulation_templates_for_user(db: SQLAlchemy, user_id: int) -> list[models.SimulationTemplate]:
    return list(db.session.execute(
        db.select(models.SimulationTemplate)
        .options(joinedload(models.SimulationTemplate.steps))
        .filter_by(user_id=user_id)
        .order_by(models.SimulationTemplate.name)
    ).scalars().unique()) # <-- THIS IS THE ENTIRE FIX

def update_simulation_template(db: SQLAlchemy, template_id: int, user_id: int, is_admin: bool, update_data: schemas.SimulationTemplateUpdate) -> models.SimulationTemplate | None:
    db_template = get_simulation_template_by_id(db, template_id)
    if not db_template:
        return None
    if not is_admin and db_template.user_id != user_id:
        return None # Unauthorized, you bastard

    # Update template fields
    update_dict = update_data.model_dump(exclude_unset=True)
    if 'name' in update_dict:
        db_template.name = update_dict['name']
    if 'description' in update_dict:
        db_template.description = update_dict['description']

    # Handle steps - this is a full replacement for simplicity
    if 'steps' in update_dict:
        # Delete old steps
        db.session.query(models.SimulationStep).filter_by(template_id=template_id).delete()
        # Add new steps
        for step_data in update_data.steps: # type: ignore
            db_step = models.SimulationStep(**step_data.model_dump())
            db_step.template_id = template_id
            db.session.add(db_step)

    db.session.commit()
    db.session.refresh(db_template)
    return db_template

def delete_simulation_template(db: SQLAlchemy, template_id: int, user_id: int, is_admin: bool) -> bool:
    db_template = get_simulation_template_by_id(db, template_id)
    if not db_template:
        return False
    if not is_admin and db_template.user_id != user_id:
        return False

    db.session.delete(db_template)
    db.session.commit()
    return True

def get_simulation_run_by_id(
    db: SQLAlchemy,
    run_id: int,
    *,
    with_events: bool = False,
) -> models.SimulationRun | None:
    """Gets a simulation run, optionally eager loading the associated events."""
    query = db.session.query(models.SimulationRun).options(
        joinedload(models.SimulationRun.template).joinedload(models.SimulationTemplate.steps)
    )

    if with_events:
        query = query.options(joinedload(models.SimulationRun.events))

    return query.filter(models.SimulationRun.id == run_id).one_or_none()


def get_simulation_run_events(
    db: SQLAlchemy,
    run_id: int,
    *,
    limit: int | None = None,
    offset: int = 0,
    order: str = "desc",
) -> tuple[list[models.SimulationRunEvent], int]:
    """Fetches simulation run events with pagination metadata."""

    total_events = db.session.scalar(
        db.select(func.count(models.SimulationRunEvent.id)).filter(models.SimulationRunEvent.run_id == run_id)
    ) or 0

    order_normalized = (order or "asc").lower()
    if order_normalized not in {"asc", "desc"}:
        order_normalized = "asc"

    query = db.session.query(models.SimulationRunEvent).filter_by(run_id=run_id)

    if order_normalized == "desc":
        query = query.order_by(
            models.SimulationRunEvent.timestamp.desc(),
            models.SimulationRunEvent.id.desc(),
        )
    else:
        query = query.order_by(
            models.SimulationRunEvent.timestamp.asc(),
            models.SimulationRunEvent.id.asc(),
        )

    if offset:
        query = query.offset(max(offset, 0))

    if limit:
        query = query.limit(max(limit, 0))

    events = list(query.all())

    if order_normalized == "desc":
        events.reverse()

    return events, total_events

def get_simulation_runs_for_user(db: SQLAlchemy, user_id: int) -> list[models.SimulationRun]:
    """Gets all simulation run summaries for a user."""
    return list(db.session.execute(
        db.select(models.SimulationRun)
        .filter_by(user_id=user_id)
        .order_by(models.SimulationRun.started_at.desc().nulls_last(), models.SimulationRun.id.desc())
    ).scalars())

def request_simulation_run_cancel(db: SQLAlchemy, run_id: int, user_id: int, is_admin: bool) -> tuple[models.SimulationRun | None, str | None]:
    """Mark a simulation run for cancellation if it is still in progress."""
    run = db.session.get(models.SimulationRun, run_id)
    if not run:
        return None, "Run not found"

    if not is_admin and run.user_id != user_id:
        return None, "Unauthorized"

    if run.status in {'COMPLETED', 'ERROR', 'FAILED', 'CANCELLED'}:
        return run, "Run is already finished"

    run.status = 'CANCELLED'
    db.session.commit()
    return run, None

def delete_simulation_run(db: SQLAlchemy, run_id: int, user_id: int, is_admin: bool) -> bool:
    """Deletes a single simulation run by its ID, checking for ownership."""
    db_run = get_simulation_run_by_id(db, run_id)
    if not db_run:
        return False # Not found
    
    # Check if the user owns this run or is an admin
    if not is_admin and db_run.user_id != user_id:
        return False # Unauthorized, you sneak

    db.session.delete(db_run)
    db.session.commit()
    return True

def delete_all_simulation_runs_for_user(db: SQLAlchemy, user_id: int):
    """
    Deletes all simulation runs for a user, respecting ORM cascade rules.
    """
    # --- THIS IS THE FIX ---
    # Fetch all the runs for the user first.
    runs_to_delete = db.session.scalars(
        db.select(models.SimulationRun).filter_by(user_id=user_id)
    ).all()
    
    # Loop and delete them one by one. This allows the ORM to see the
    # cascade rule and delete the associated events for each run.
    for run in runs_to_delete:
        db.session.delete(run)
    
    db.session.commit()


def calculate_simulation_run_stats(run: models.SimulationRun) -> dict[str, Any]:
    """Builds an aggregate statistics payload for a simulation run."""
    events = sorted(run.events, key=lambda e: e.timestamp or datetime.utcnow())

    total_events = len(events)
    success_events = 0
    failure_events = 0
    warning_events = 0
    info_events = 0
    debug_events = 0

    steps: dict[int, dict[str, int]] = {}
    last_failure_details: str | None = None

    for event in events:
        status = (event.status or '').upper()
        step_stats = steps.setdefault(event.step_order, {
            'total': 0,
            'success': 0,
            'failure': 0,
            'warning': 0,
            'info': 0,
        })

        step_stats['total'] += 1

        if status == 'SUCCESS':
            success_events += 1
            step_stats['success'] += 1
        elif status in ('FAILURE', 'ERROR'):
            failure_events += 1
            step_stats['failure'] += 1
            timestamp = event.timestamp.isoformat() if event.timestamp else 'unknown-time'
            last_failure_details = f"[{timestamp}] Step {event.step_order} Iter {event.iteration}: {event.details}"
        elif status == 'WARN':
            warning_events += 1
            step_stats['warning'] += 1
        elif status == 'INFO':
            info_events += 1
            step_stats['info'] += 1
        elif status == 'DEBUG':
            debug_events += 1
        else:
            info_events += 1
            step_stats['info'] += 1

    first_event_at = events[0].timestamp if events else None
    last_event_at = events[-1].timestamp if events else None

    started_at = run.started_at or first_event_at
    completed_at = run.completed_at or last_event_at
    duration_seconds = None
    if started_at and completed_at:
        duration_seconds = (completed_at - started_at).total_seconds()

    max_iteration = max((event.iteration for event in events), default=0)

    step_stats_payload = [
        {
            'step_order': step_order,
            'total_events': stats['total'],
            'success_events': stats['success'],
            'failure_events': stats['failure'],
            'warning_events': stats['warning'],
            'info_events': stats['info'],
        }
        for step_order, stats in sorted(steps.items())
    ]

    duration_summary: list[dict[str, Any]] = []
    stats_record = getattr(run, 'stats', None)
    if stats_record and isinstance(stats_record.step_duration_summary, dict):
        for key, entry in stats_record.step_duration_summary.items():
            try:
                step_order = int(entry.get('step_order', key))
            except (TypeError, ValueError):
                step_order = key
            count = int(entry.get('count', 0)) or 0
            total_ms = float(entry.get('total_ms', 0.0)) if entry.get('total_ms') is not None else 0.0
            avg_ms = total_ms / count if count else None
            min_ms = entry.get('min_ms')
            if min_ms is not None:
                min_ms = float(min_ms)
            max_ms = entry.get('max_ms')
            if max_ms is not None:
                max_ms = float(max_ms)
            last_ms = entry.get('last_ms')
            if last_ms is not None:
                last_ms = float(last_ms)
            duration_summary.append({
                'step_order': step_order,
                'step_type': entry.get('step_type'),
                'count': count,
                'total_ms': total_ms,
                'avg_ms': avg_ms,
                'min_ms': min_ms,
                'max_ms': max_ms,
                'last_ms': last_ms,
            })
        duration_summary.sort(key=lambda item: item.get('step_order', 0))

    return {
        'run_id': run.id,
        'user_id': run.user_id,
        'template_id': run.template_id,
        'patient_count': run.patient_count,
        'status': run.status,
        'started_at': started_at,
        'completed_at': completed_at,
        'duration_seconds': duration_seconds,
        'first_event_at': first_event_at,
        'last_event_at': last_event_at,
        'total_events': total_events,
        'success_events': success_events,
        'failure_events': failure_events,
        'warning_events': warning_events,
        'info_events': info_events,
        'debug_events': debug_events,
        'unique_steps': len(steps),
        'max_iteration': max_iteration,
        'last_failure': last_failure_details,
        'steps': step_stats_payload,
        'step_duration_summary': duration_summary,
    }


def _ensure_run_stats(db: SQLAlchemy, run_id: int) -> models.SimulationRunStats:
    stats = db.session.execute(
        select(models.SimulationRunStats).filter_by(run_id=run_id)
    ).scalar_one_or_none()
    if stats:
        return stats

    run = db.session.get(models.SimulationRun, run_id)
    if not run:
        raise ValueError(f"SimulationRun {run_id} not found; cannot create stats entry")

    stats = models.SimulationRunStats()
    stats.run_id = run_id
    stats.total_patients = run.patient_count or 1
    db.session.add(stats)
    db.session.flush()
    return stats


def record_queue_publish_metric(
    db: SQLAlchemy,
    run_id: int,
    *,
    latency_ms: float,
    queued_jobs: int,
) -> models.SimulationRunStats:
    stats = _ensure_run_stats(db, run_id)
    stats.queued_job_count += 1
    stats.queue_publish_sum_ms += float(latency_ms)
    stats.queue_publish_min_ms = (
        latency_ms
        if stats.queue_publish_min_ms is None or latency_ms < stats.queue_publish_min_ms
        else stats.queue_publish_min_ms
    )
    stats.queue_publish_max_ms = (
        latency_ms
        if stats.queue_publish_max_ms is None or latency_ms > stats.queue_publish_max_ms
        else stats.queue_publish_max_ms
    )
    stats.queued_job_last_depth = queued_jobs
    if queued_jobs > stats.queued_job_max_depth:
        stats.queued_job_max_depth = queued_jobs
    db.session.commit()
    return stats


def record_dicom_send_metric(
    db: SQLAlchemy,
    run_id: int,
    *,
    attempted_instances: int,
    success_instances: int,
    attempted_bytes: int,
    success_bytes: int,
    duration_ms: float,
) -> models.SimulationRunStats:
    stats = _ensure_run_stats(db, run_id)
    stats.dicom_attempted_instances += int(attempted_instances)
    stats.dicom_success_instances += int(success_instances)
    stats.dicom_attempted_bytes += int(attempted_bytes)
    stats.dicom_success_bytes += int(success_bytes)
    stats.dicom_send_count += 1
    stats.dicom_send_sum_ms += float(duration_ms)
    stats.dicom_send_min_ms = (
        duration_ms
        if stats.dicom_send_min_ms is None or duration_ms < stats.dicom_send_min_ms
        else stats.dicom_send_min_ms
    )
    stats.dicom_send_max_ms = (
        duration_ms
        if stats.dicom_send_max_ms is None or duration_ms > stats.dicom_send_max_ms
        else stats.dicom_send_max_ms
    )

    throughput_mbps = None
    if success_bytes > 0 and duration_ms > 0:
        seconds = duration_ms / 1000.0
        if seconds > 0:
            throughput_mbps = (success_bytes * 8.0) / seconds / 1_000_000

    if throughput_mbps is not None:
        stats.dicom_throughput_count += 1
        stats.dicom_throughput_sum_mbps += throughput_mbps
        stats.dicom_throughput_min_mbps = (
            throughput_mbps
            if stats.dicom_throughput_min_mbps is None or throughput_mbps < stats.dicom_throughput_min_mbps
            else stats.dicom_throughput_min_mbps
        )
        stats.dicom_throughput_max_mbps = (
            throughput_mbps
            if stats.dicom_throughput_max_mbps is None or throughput_mbps > stats.dicom_throughput_max_mbps
            else stats.dicom_throughput_max_mbps
        )
    db.session.commit()
    return stats


def record_step_duration_metric(
    db: SQLAlchemy,
    *,
    run_id: int,
    step_order: int,
    step_type: str,
    duration_ms: float,
) -> models.SimulationRunStats:
    stats = _ensure_run_stats(db, run_id)
    summary = dict(stats.step_duration_summary or {})
    key = str(step_order)
    entry = summary.get(key, {
        'step_order': step_order,
        'step_type': step_type,
        'count': 0,
        'total_ms': 0.0,
        'min_ms': None,
        'max_ms': None,
    })

    entry['step_type'] = step_type
    entry['count'] = int(entry.get('count', 0)) + 1
    entry['total_ms'] = float(entry.get('total_ms', 0.0)) + float(duration_ms)
    entry['min_ms'] = (
        float(duration_ms)
        if entry.get('min_ms') is None or duration_ms < entry.get('min_ms')
        else entry.get('min_ms')
    )
    entry['max_ms'] = (
        float(duration_ms)
        if entry.get('max_ms') is None or duration_ms > entry.get('max_ms')
        else entry.get('max_ms')
    )
    entry['last_ms'] = float(duration_ms)

    summary[key] = entry
    stats.step_duration_summary = summary
    db.session.commit()
    return stats


def record_worker_job_metric(
    db: SQLAlchemy,
    *,
    run_id: int,
    job_id: str | None,
    queue: str | None,
    success: bool,
    outcome: str,
    error: str | None,
    duration_ms: float | None,
    steps_executed: int,
    remaining_steps: int,
    patient_iteration: int | None,
    repeat_iteration: int | None,
) -> models.WorkerJobMetric:
    metric = models.WorkerJobMetric()
    metric.run_id = run_id
    metric.job_id = job_id
    metric.queue = queue
    metric.success = success
    metric.outcome = outcome
    metric.error = error
    metric.duration_ms = duration_ms
    metric.steps_executed = steps_executed
    metric.remaining_steps = remaining_steps
    metric.patient_iteration = patient_iteration
    metric.repeat_iteration = repeat_iteration
    db.session.add(metric)

    stats = _ensure_run_stats(db, run_id)
    stats.worker_job_count += 1
    if success:
        stats.worker_job_success_count += 1
    if duration_ms is not None:
        stats.worker_job_duration_sum_ms += float(duration_ms)
        stats.worker_job_duration_min_ms = (
            duration_ms
            if stats.worker_job_duration_min_ms is None or duration_ms < stats.worker_job_duration_min_ms
            else stats.worker_job_duration_min_ms
        )
        stats.worker_job_duration_max_ms = (
            duration_ms
            if stats.worker_job_duration_max_ms is None or duration_ms > stats.worker_job_duration_max_ms
            else stats.worker_job_duration_max_ms
        )
    db.session.commit()
    db.session.refresh(metric)
    return metric


def get_run_stats_record(db: SQLAlchemy, run_id: int, *, create_if_missing: bool = False) -> models.SimulationRunStats | None:
    stats = db.session.execute(
        select(models.SimulationRunStats).filter_by(run_id=run_id)
    ).scalar_one_or_none()
    if stats or not create_if_missing:
        return stats
    return _ensure_run_stats(db, run_id)


def get_worker_metrics_for_run(
    db: SQLAlchemy,
    run_id: int,
    *,
    limit: int | None = None,
    offset: int = 0,
    order: str = "asc",
) -> tuple[list[models.WorkerJobMetric], int]:
    """Fetch worker metrics for a run with optional pagination."""
    total_count = db.session.execute(
        select(func.count()).select_from(models.WorkerJobMetric).filter_by(run_id=run_id)
    ).scalar_one()

    order_normalized = (order or "asc").lower()
    if order_normalized not in {"asc", "desc"}:
        order_normalized = "asc"

    query = select(models.WorkerJobMetric).filter_by(run_id=run_id)
    if order_normalized == "desc":
        query = query.order_by(
            models.WorkerJobMetric.created_at.desc(),
            models.WorkerJobMetric.id.desc(),
        )
    else:
        query = query.order_by(
            models.WorkerJobMetric.created_at.asc(),
            models.WorkerJobMetric.id.asc(),
        )

    if offset:
        query = query.offset(max(offset, 0))
    if limit:
        query = query.limit(max(limit, 0))

    metrics = list(db.session.execute(query).scalars())
    return metrics, total_count


def update_run_timing_metrics(db: SQLAlchemy, run_id: int) -> models.SimulationRunStats | None:
    run = db.session.get(models.SimulationRun, run_id)
    if not run:
        return None

    stats = _ensure_run_stats(db, run_id)
    if run.started_at and run.completed_at:
        wall_clock_seconds = (run.completed_at - run.started_at).total_seconds()
        stats.wall_clock_seconds = wall_clock_seconds
        if wall_clock_seconds > 0 and stats.queued_job_count:
            stats.orders_per_second = stats.queued_job_count / wall_clock_seconds
    db.session.commit()
    return stats


def _compute_average(total: float | int, count: int) -> float | None:
    if not count:
        return None
    return float(total) / float(count)


def build_run_metrics_payload(
    stats: models.SimulationRunStats,
    *,
    run: models.SimulationRun | None = None,
    user: models.User | None = None,
    template: models.SimulationTemplate | None = None,
) -> dict[str, Any]:
    queue_publish_sum = float(stats.queue_publish_sum_ms or 0.0)
    dicom_send_sum = float(stats.dicom_send_sum_ms or 0.0)
    worker_duration_sum = float(stats.worker_job_duration_sum_ms or 0.0)
    dicom_throughput_sum = float(stats.dicom_throughput_sum_mbps or 0.0)

    queue_avg = _compute_average(queue_publish_sum, stats.queued_job_count)
    dicom_avg = _compute_average(dicom_send_sum, stats.dicom_send_count)
    worker_avg = _compute_average(worker_duration_sum, stats.worker_job_count)
    dicom_throughput_avg = _compute_average(dicom_throughput_sum, stats.dicom_throughput_count)

    if run is None:
        run = stats.run
    if template is None and run is not None:
        template = getattr(run, "template", None)
    if user is None and run is not None:
        user = getattr(run, "user", None)

    step_duration_payload: list[dict[str, Any]] = []
    if isinstance(stats.step_duration_summary, dict):
        for key, entry in stats.step_duration_summary.items():
            try:
                step_order = int(entry.get('step_order', key))
            except (TypeError, ValueError):
                step_order = key
            count = int(entry.get('count', 0)) or 0
            total_ms = float(entry.get('total_ms', 0.0)) if entry.get('total_ms') is not None else 0.0
            avg_ms = total_ms / count if count else None
            min_ms = entry.get('min_ms')
            if min_ms is not None:
                min_ms = float(min_ms)
            max_ms = entry.get('max_ms')
            if max_ms is not None:
                max_ms = float(max_ms)
            last_ms = entry.get('last_ms')
            if last_ms is not None:
                last_ms = float(last_ms)

            step_duration_payload.append({
                'step_order': step_order,
                'step_type': entry.get('step_type'),
                'count': count,
                'total_ms': total_ms,
                'avg_ms': avg_ms,
                'min_ms': min_ms,
                'max_ms': max_ms,
                'last_ms': last_ms,
            })
        step_duration_payload.sort(key=lambda item: item.get('step_order', 0))

    return {
        "run_id": stats.run_id,
        "user_id": getattr(run, "user_id", None),
        "username": getattr(user, "username", None) if user else None,
        "template_id": getattr(run, "template_id", None),
        "template_name": getattr(template, "name", None) if template else None,
        "status": getattr(run, "status", None),
        "started_at": getattr(run, "started_at", None),
        "completed_at": getattr(run, "completed_at", None),
        "total_patients": stats.total_patients,
        "queued_job_count": stats.queued_job_count,
        "queued_job_max_depth": stats.queued_job_max_depth,
        "queued_job_last_depth": stats.queued_job_last_depth,
    "queue_publish_sum_ms": queue_publish_sum,
        "queue_publish_min_ms": stats.queue_publish_min_ms,
        "queue_publish_max_ms": stats.queue_publish_max_ms,
        "queue_publish_avg_ms": queue_avg,
        "dicom_attempted_instances": stats.dicom_attempted_instances,
        "dicom_success_instances": stats.dicom_success_instances,
        "dicom_attempted_bytes": stats.dicom_attempted_bytes,
        "dicom_success_bytes": stats.dicom_success_bytes,
        "dicom_send_count": stats.dicom_send_count,
    "dicom_send_sum_ms": dicom_send_sum,
        "dicom_send_min_ms": stats.dicom_send_min_ms,
        "dicom_send_max_ms": stats.dicom_send_max_ms,
        "dicom_send_avg_ms": dicom_avg,
    "dicom_throughput_sum_mbps": dicom_throughput_sum,
        "dicom_throughput_min_mbps": stats.dicom_throughput_min_mbps,
        "dicom_throughput_max_mbps": stats.dicom_throughput_max_mbps,
        "dicom_throughput_avg_mbps": dicom_throughput_avg,
        "dicom_throughput_count": stats.dicom_throughput_count,
        "worker_job_count": stats.worker_job_count,
        "worker_job_success_count": stats.worker_job_success_count,
    "worker_job_duration_sum_ms": worker_duration_sum,
        "worker_job_duration_min_ms": stats.worker_job_duration_min_ms,
        "worker_job_duration_max_ms": stats.worker_job_duration_max_ms,
        "worker_job_duration_avg_ms": worker_avg,
        "wall_clock_seconds": stats.wall_clock_seconds,
        "orders_per_second": stats.orders_per_second,
        "step_durations": step_duration_payload,
        "created_at": stats.created_at,
        "updated_at": stats.updated_at,
    }


def list_run_metrics(
    db: SQLAlchemy,
    *,
    user_id: int,
    is_admin: bool,
    template_id: int | None = None,
    status: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = (
        db.session.query(models.SimulationRunStats, models.SimulationRun, models.User, models.SimulationTemplate)
        .join(models.SimulationRun, models.SimulationRun.id == models.SimulationRunStats.run_id)
        .join(models.User, models.User.id == models.SimulationRun.user_id)
        .outerjoin(models.SimulationTemplate, models.SimulationTemplate.id == models.SimulationRun.template_id)
    )

    if not is_admin:
        query = query.filter(models.SimulationRun.user_id == user_id)
    if template_id is not None:
        query = query.filter(models.SimulationRun.template_id == template_id)
    if status:
        query = query.filter(models.SimulationRun.status == status)
    if start_at:
        query = query.filter(models.SimulationRun.started_at >= start_at)
    if end_at:
        query = query.filter(models.SimulationRun.completed_at <= end_at)

    query = query.order_by(models.SimulationRunStats.created_at.desc())
    if limit:
        query = query.limit(max(limit, 0))

    results: list[dict[str, Any]] = []
    for stats, run, user, template in query.all():
        results.append(build_run_metrics_payload(stats, run=run, user=user, template=template))
    return results


def list_worker_metrics(
    db: SQLAlchemy,
    *,
    user_id: int,
    is_admin: bool,
    run_id: int | None = None,
    queue: str | None = None,
    success: bool | None = None,
    limit: int = 200,
) -> list[models.WorkerJobMetric]:
    query = db.session.query(models.WorkerJobMetric).join(models.SimulationRun)

    if not is_admin:
        query = query.filter(models.SimulationRun.user_id == user_id)
    if run_id is not None:
        query = query.filter(models.WorkerJobMetric.run_id == run_id)
    if queue:
        query = query.filter(models.WorkerJobMetric.queue == queue)
    if success is not None:
        query = query.filter(models.WorkerJobMetric.success == success)

    query = query.order_by(models.WorkerJobMetric.created_at.desc())
    if limit:
        query = query.limit(max(limit, 0))

    return list(query.all())


def create_api_key(db: SQLAlchemy, user_id: int, name: str) -> tuple[models.ApiKey, str]:
    """Generates a new API key, stores its hash, and returns the key object and the raw key."""
    raw_key = f"ytr_{secrets.token_urlsafe(32)}"
    key_prefix = raw_key[:8]
    key_hash = bcrypt.generate_password_hash(raw_key).decode('utf-8')
    
    db_key = models.ApiKey(user_id=user_id, name=name, key_hash=key_hash, key_prefix=key_prefix)
    db.session.add(db_key)
    db.session.commit()
    db.session.refresh(db_key)
    return db_key, raw_key

def get_api_key_by_prefix(db: SQLAlchemy, key_prefix: str) -> models.ApiKey | None:
    """Finds an API key by its non-secret prefix."""
    return db.session.execute(
        db.select(models.ApiKey).filter_by(key_prefix=key_prefix)
    ).scalar_one_or_none()
    
def get_api_keys_for_user(db: SQLAlchemy, user_id: int) -> list[models.ApiKey]:
    """Gets all API keys for a given user."""
    return list(db.session.scalars(
        db.select(models.ApiKey).filter_by(user_id=user_id).order_by(models.ApiKey.created_at.desc())
    ))

def delete_api_key(db: SQLAlchemy, key_id: int, user_id: int) -> bool:
    """Deletes an API key, ensuring the user has ownership."""
    db_key = db.session.get(models.ApiKey, key_id)
    if db_key and db_key.user_id == user_id:
        db.session.delete(db_key)
        db.session.commit()
        return True
    return False

def update_api_key_last_used(db: SQLAlchemy, key_prefix: str):
    """Updates the last_used timestamp for a key."""
    db_key = get_api_key_by_prefix(db, key_prefix)
    if db_key:
        db_key.last_used = datetime.utcnow()
        db.session.commit()
# --- END OF FILE app/crud.py ---