# --- START OF FILE app/crud.py ---

from sqlalchemy.orm import Session
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy # <-- NEW IMPORT

from . import models, schemas
from .extensions import bcrypt # We can import this directly now

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
    hashed_password = bcrypt.generate_password_hash(user.password).decode('utf-8')
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password
    )
    db.session.add(db_user)
    db.session.commit()
    db.session.refresh(db_user)
    return db_user

def create_google_user(db: SQLAlchemy, email: str, username: str, google_id: str) -> models.User:
    placeholder_hash = bcrypt.generate_password_hash("!@#$Unusabl3P@ssw0rdForG00gl3Log!n#@$!").decode('utf-8')
    db_user = models.User(
        username=username,
        email=email,
        password_hash=placeholder_hash,
        google_id=google_id
    )
    db.session.add(db_user)
    db.session.commit()
    db.session.refresh(db_user)
    return db_user


# --- Template CRUD ---

def get_templates_for_user(db: SQLAlchemy, user_id: int) -> list[models.UserTemplate]:
    # Explicitly cast to list[models.UserTemplate] for type checkers
    return list(db.session.execute(
        db.select(models.UserTemplate)
        .filter_by(user_id=user_id)
        .order_by(models.UserTemplate.name)
    ).scalars())

def create_template(db: SQLAlchemy, user_id: int, template: schemas.TemplateCreate) -> models.UserTemplate:
    db_template = models.UserTemplate(
        user_id=user_id,
        name=template.name,
        content=template.content
    )
    db.session.add(db_template)
    db.session.commit()
    db.session.refresh(db_template)
    return db_template

def delete_template(db: SQLAlchemy, user_id: int, template_id: int) -> models.UserTemplate | None:
    db_template = db.session.execute(
        db.select(models.UserTemplate).filter_by(id=template_id, user_id=user_id)
    ).scalar_one_or_none()
    
    if db_template:
        db.session.delete(db_template)
        db.session.commit()
    return db_template

# --- Token Usage CRUD ---

def record_token_usage(db: SQLAlchemy, user_id: int, model_name: str, usage_data: dict) -> models.TokenUsage:
    db_usage = models.TokenUsage(
        user_id=user_id,
        model=model_name,
        input_tokens=usage_data.get('input_tokens', 0),
        output_tokens=usage_data.get('output_tokens', 0),
        total_tokens=usage_data.get('total_tokens', 0)
    )
    db.session.add(db_usage)
    db.session.commit()
    db.session.refresh(db_usage)
    return db_usage

def get_total_usage_for_user(db: SQLAlchemy, user_id: int) -> int:
    total = db.session.scalar(
        db.select(func.sum(models.TokenUsage.total_tokens)).filter_by(user_id=user_id)
    )
    return total or 0

def get_usage_by_model_for_user(db: SQLAlchemy, user_id: int) -> dict:
    results = db.session.execute(
        db.select(models.TokenUsage.model, func.sum(models.TokenUsage.total_tokens))
        .filter_by(user_id=user_id).group_by(models.TokenUsage.model)
    ).all()
    return {model: total for model, total in results}

# --- END OF FILE app/crud.py ---