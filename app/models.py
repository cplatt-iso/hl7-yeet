# --- START OF FILE app/models.py ---
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Any, Optional 

from .extensions import db

class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # --- THE FIX: Use Optional[str] for Python 3.9 compatibility ---
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    templates: Mapped[List["UserTemplate"]] = relationship("UserTemplate", back_populates="user", cascade="all, delete-orphan")
    token_usages: Mapped[List["TokenUsage"]] = relationship("TokenUsage", back_populates="user", cascade="all, delete-orphan")

    # --- THE FIX: Also update the type hint in the constructor ---
    def __init__(self, username: str, email: str, password_hash: str, google_id: Optional[str] = None, **kw: Any):
        super().__init__(**kw)
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.google_id = google_id

    def __repr__(self):
        return f'<User {self.username}>'

class UserTemplate(db.Model):
    __tablename__ = "user_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
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

    # Relationships
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
    
class Hl7TableDefinition(db.Model):
    __tablename__ = 'hl7_table_definitions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_id: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(10), nullable=False, default="2.5.1")

    def __init__(self, table_id: str, value: str, description: str, version: str = "2.5.1", **kw: Any):
        super().__init__(**kw)
        self.table_id = table_id
        self.value = value
        self.description = description
        self.version = version

    def __repr__(self):
        return f'<Hl7TableDefinition {self.table_id}:{self.value}>'

# --- END OF FILE app/models.py ---