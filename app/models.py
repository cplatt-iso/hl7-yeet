# --- START OF FILE app/models.py ---
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Any, Optional 

from .extensions import db

# ... (User, UserTemplate, TokenUsage, Hl7Destination, Hl7TableDefinition models are unchanged) ...

class User(db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    templates: Mapped[List["UserTemplate"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    token_usages: Mapped[List["TokenUsage"]] = relationship("TokenUsage", back_populates="user", cascade="all, delete-orphan")
    destinations: Mapped[List["Hl7Destination"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    hl7_versions: Mapped[List["Hl7Version"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    def __init__(self, username: str, email: str, password_hash: str, google_id: Optional[str] = None, is_admin: bool = False, **kw: Any):
        super().__init__(**kw)
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.google_id = google_id
        self.is_admin = is_admin
    def __repr__(self):
        return f'<User {self.username} (Admin: {self.is_admin})>'

class UserTemplate(db.Model):
    __tablename__ = "user_templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped["User"] = relationship("User", back_populates="templates")
    def __init__(self, user_id: int, name: str, content: str, **kw: Any):
        super().__init__(**kw)
        self.user_id = user_id
        self.name = name
        self.content = content
    def __repr__(self):
        return f'<UserTemplate {self.name}>'

class TokenUsage(db.Model):
    __tablename__ = "token_usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped["User"] = relationship("User", back_populates="token_usages")
    def __init__(self, user_id: int, model: str, input_tokens: int, output_tokens: int, total_tokens: int, **kw: Any):
        super().__init__(**kw)
        self.user_id = user_id
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
    def __repr__(self):
        return f'<TokenUsage user_id={self.user_id} model={self.model} tokens={self.total_tokens}>'

class Hl7Destination(db.Model):
    __tablename__ = 'hl7_destinations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="destinations")
    def __init__(self, user_id: int, name: str, hostname: str, port: int, **kw: Any):
        super().__init__(**kw)
        self.user_id = user_id
        self.name = name
        self.hostname = hostname
        self.port = port
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'hostname': self.hostname, 'port': self.port}
    def __repr__(self):
        return f'<Hl7Destination {self.name} ({self.hostname}:{self.port})>'

class Hl7TableDefinition(db.Model):
    __tablename__ = 'hl7_table_definitions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_id: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    def __init__(self, table_id: str, value: str, description: str, **kw: Any):
        super().__init__(**kw)
        self.table_id = table_id
        self.value = value
        self.description = description
    def __repr__(self):
        return f'<Hl7TableDefinition {self.table_id}:{self.value}>'

class Hl7Version(db.Model):
    __tablename__ = 'hl7_versions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="hl7_versions")
    def __init__(self, version: str, description: Optional[str], user_id: int, is_active: bool = True, **kw: Any):
        super().__init__(**kw)
        self.version = version
        self.description = description
        self.user_id = user_id
        self.is_active = is_active
    def to_dict(self):
        return {'id': self.id, 'version': self.version, 'description': self.description, 'is_active': self.is_active, 'processed_at': self.processed_at.isoformat(), 'processed_by': self.user.username if self.user else 'Unknown'}
    def __repr__(self):
        return f'<Hl7Version {self.version} (Active: {self.is_active})>'

class SystemMetadata(db.Model):
    __tablename__ = 'system_metadata'
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    def __init__(self, key: str, value: str, **kw: Any):
        super().__init__(**kw)
        self.key = key
        self.value = value

class ReceivedMessage(db.Model):
    __tablename__ = 'received_messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    control_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    sending_app: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    
    # --- THIS IS THE FIX ---
    # Adding an explicit __init__ makes Pylance happy and our code clearer.
    def __init__(self, raw_message: str, message_type: str, control_id: str, sending_app: str, **kw: Any):
        super().__init__(**kw)
        self.raw_message = raw_message
        self.message_type = message_type
        self.control_id = control_id
        self.sending_app = sending_app

    def to_summary_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'message_type': self.message_type,
            'control_id': self.control_id,
            'sending_app': self.sending_app,
        }
# --- END OF FILE app/models.py ---