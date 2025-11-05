# --- START OF FILE app/models.py ---
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func, Boolean, JSON, Float, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Any, Optional 

from .extensions import db

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
    
    # --- RENAMED RELATIONSHIP ---
    endpoints: Mapped[List["Endpoint"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    hl7_versions: Mapped[List["Hl7Version"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    # --- NEW RELATIONSHIPS FOR SIMULATOR ---
    generator_templates: Mapped[List["GeneratorTemplate"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    simulation_templates: Mapped[List["SimulationTemplate"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    simulation_runs: Mapped[List["SimulationRun"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    api_keys: Mapped[List["ApiKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")

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

# --- RENAMED FROM Hl7Destination ---
class Endpoint(db.Model):
    __tablename__ = 'endpoints'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # --- NEW FIELDS ---
    endpoint_type: Mapped[str] = mapped_column(String(20), nullable=False, default='MLLP') # 'MLLP', 'DICOM_SCP'
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    ae_title: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # For DICOM
    aet_title: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # Our AE Title when calling

    user: Mapped["User"] = relationship("User", back_populates="endpoints")

    def __init__(self, user_id: int, name: str, endpoint_type: str, hostname: str, port: int, ae_title: Optional[str] = None, aet_title: Optional[str] = None, **kw: Any):
        super().__init__(**kw)
        self.user_id = user_id
        self.name = name
        self.endpoint_type = endpoint_type
        self.hostname = hostname
        self.port = port
        self.ae_title = ae_title
        self.aet_title = aet_title

    def to_dict(self):
        return {'id': self.id, 'user_id': self.user_id, 'name': self.name, 'endpoint_type': self.endpoint_type, 'hostname': self.hostname, 'port': self.port, 'ae_title': self.ae_title, 'aet_title': self.aet_title}

    def __repr__(self):
        return f'<Endpoint {self.name} ({self.endpoint_type}@{self.hostname}:{self.port})>'


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
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # <-- ADD THIS
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="hl7_versions")
    def __init__(self, version: str, description: Optional[str], user_id: int, is_active: bool = True, is_default: bool = False, **kw: Any): # <-- MODIFY
        super().__init__(**kw)
        self.version = version
        self.description = description
        self.user_id = user_id
        self.is_active = is_active
        self.is_default = is_default # <-- ADD THIS
    def to_dict(self):
        return {'id': self.id, 'version': self.version, 'description': self.description, 'is_active': self.is_active, 'is_default': self.is_default, 'processed_at': self.processed_at.isoformat(), 'processed_by': self.user.username if self.user else 'Unknown'} # <-- MODIFY
    def __repr__(self):
        return f'<Hl7Version {self.version} (Active: {self.is_active}, Default: {self.is_default})>' 

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

# --- NEW SIMULATOR MODELS ---

class GeneratorTemplate(db.Model):
    __tablename__ = "generator_templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped["User"] = relationship("User", back_populates="generator_templates")

class SimulationTemplate(db.Model):
    __tablename__ = "simulation_templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped["User"] = relationship("User", back_populates="simulation_templates")
    steps: Mapped[List["SimulationStep"]] = relationship(back_populates="template", cascade="all, delete-orphan", order_by="SimulationStep.step_order")

class SimulationStep(db.Model):
    __tablename__ = "simulation_steps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("simulation_templates.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    template: Mapped["SimulationTemplate"] = relationship("SimulationTemplate", back_populates="steps")

class SimulationRun(db.Model):
    __tablename__ = "simulation_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("simulation_templates.id"), nullable=False)
    patient_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    template: Mapped["SimulationTemplate"] = relationship("SimulationTemplate")
    status: Mapped[str] = mapped_column(String(20), default='PENDING', nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    user: Mapped["User"] = relationship("User", back_populates="simulation_runs")
    
    # --- THIS IS THE FIX ---
    # Tell SQLAlchemy to cascade deletes from a SimulationRun to its Events
    events: Mapped[List["SimulationRunEvent"]] = relationship(back_populates="run", cascade="all, delete-orphan", order_by="SimulationRunEvent.timestamp")
    stats: Mapped[Optional["SimulationRunStats"]] = relationship("SimulationRunStats", back_populates="run", cascade="all, delete-orphan", uselist=False)
    worker_metrics: Mapped[List["WorkerJobMetric"]] = relationship("WorkerJobMetric", back_populates="run", cascade="all, delete-orphan")

class SimulationRunEvent(db.Model):
    __tablename__ = "simulation_run_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("simulation_runs.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False) # 'SUCCESS', 'FAILURE', 'INFO'
    details: Mapped[str] = mapped_column(Text, nullable=False)
    run: Mapped["SimulationRun"] = relationship("SimulationRun", back_populates="events")

    def __init__(self, run_id: int, step_order: int, iteration: int, status: str, details: str, **kw: Any):
        super().__init__(**kw)
        self.run_id = run_id
        self.step_order = step_order
        self.iteration = iteration
        self.status = status
        self.details = details

class SimulationRunStats(db.Model):
    __tablename__ = "simulation_run_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("simulation_runs.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_patients: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    queued_job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    queued_job_max_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    queued_job_last_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    queue_publish_sum_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    queue_publish_min_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    queue_publish_max_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dicom_attempted_instances: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dicom_success_instances: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dicom_attempted_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    dicom_success_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    dicom_send_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dicom_send_sum_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    dicom_send_min_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dicom_send_max_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    worker_job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    worker_job_success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    worker_job_duration_sum_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    worker_job_duration_min_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    worker_job_duration_max_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wall_clock_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    orders_per_second: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    run: Mapped["SimulationRun"] = relationship("SimulationRun", back_populates="stats")

class WorkerJobMetric(db.Model):
    __tablename__ = "worker_job_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    queue: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    steps_executed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remaining_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    patient_iteration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    repeat_iteration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    run: Mapped["SimulationRun"] = relationship("SimulationRun", back_populates="worker_metrics")

class ApiKey(db.Model):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Store the first 8 characters of the key so users can identify which one it is
    key_prefix: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user: Mapped["User"] = relationship("User")

    def __init__(self, user_id: int, name: str, key_hash: str, key_prefix: str, **kw: Any):
        super().__init__(**kw)
        self.user_id = user_id
        self.name = name
        self.key_hash = key_hash
        self.key_prefix = key_prefix
# --- END OF FILE app/models.py ---