# --- START OF FILE app/crud.py ---

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, select, or_
from flask_sqlalchemy import SQLAlchemy
import logging 

from . import models, schemas
from .extensions import bcrypt

# --- User CRUD ---

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

# --- Template CRUD ---

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

# --- Token Usage CRUD ---

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

# --- Hl7Version CRUD ---

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
        db.session.commit()
        db.session.refresh(version)
    return version

def get_distinct_table_ids(db: SQLAlchemy) -> list[str]:
    """Gets a sorted list of unique HL7 table IDs from the database."""
    results = db.session.execute(
        select(models.Hl7TableDefinition.table_id).distinct().order_by(models.Hl7TableDefinition.table_id)
    ).scalars().all()
    return list(results)

def get_definitions_for_table(db: SQLAlchemy, table_id: str) -> list[models.Hl7TableDefinition]:
    """Gets all definitions for a specific table ID."""
    return list(db.session.execute(
        db.select(models.Hl7TableDefinition).filter_by(table_id=table_id).order_by(models.Hl7TableDefinition.value)
    ).scalars())

def get_definition_by_id(db: SQLAlchemy, def_id: int) -> models.Hl7TableDefinition | None:
    """Gets a single definition by its primary key."""
    return db.session.get(models.Hl7TableDefinition, def_id)

def create_definition(db: SQLAlchemy, definition: schemas.DefinitionCreate) -> models.Hl7TableDefinition:
    """Creates a new table definition."""
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
    """Updates a table definition."""
    db_def = get_definition_by_id(db, def_id)
    if db_def:
        update_data = definition_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_def, key, value)
        db.session.commit()
        db.session.refresh(db_def)
    return db_def

def delete_definition(db: SQLAlchemy, def_id: int) -> bool:
    """Deletes a table definition. Returns True if successful, False otherwise."""
    db_def = get_definition_by_id(db, def_id)
    if db_def:
        db.session.delete(db_def)
        db.session.commit()
        return True
    return False

def clear_hl7_table_definitions(db: SQLAlchemy):
    # This function is used by the refresh process
    db.session.query(models.Hl7TableDefinition).delete()
    db.session.commit()

def bulk_add_hl7_table_definitions(db: SQLAlchemy, definitions: list[dict]):
    # This function is used by the refresh process
    db.session.bulk_insert_mappings(models.Hl7TableDefinition, definitions) # type: ignore
    db.session.commit()

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

def add_received_message(db: SQLAlchemy, raw_message: str) -> models.ReceivedMessage:
    """Parses key fields and adds a new received message to the database."""
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
    """Gets a paginated and filtered list of received messages."""
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
    """Deletes all records from the received_messages table."""
    db.session.query(models.ReceivedMessage).delete()
    db.session.commit()
