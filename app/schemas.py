# --- START OF FILE app/schemas.py ---
from pydantic import BaseModel, Field, EmailStr, computed_field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Pydantic Config ---
class AppBaseModel(BaseModel):
    class Config:
        from_attributes = True

# --- Auth Schemas (unchanged) ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    username: str
    password: str

class GoogleToken(BaseModel):
    token: str

class TokenResponse(BaseModel):
    access_token: str
    username: str
    is_admin: bool

class UserSchema(AppBaseModel):
    id: int
    username: str
    email: EmailStr
    is_admin: bool
    created_at: datetime

# --- Template Schemas (unchanged) ---
class TemplateBase(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)

class TemplateCreate(TemplateBase):
    pass

class Template(TemplateBase):
    id: int

# --- API Data Schemas (unchanged) ---
class MllpSendRequest(BaseModel):
    host: str
    port: int
    message: str

class MllpPingRequest(BaseModel):
    host: str
    port: int

class ParseRequest(BaseModel):
    message: str
    version: str

class AnalyzeRequest(BaseModel):
    message: str
    model: str
    version: str

# --- Listener Schemas (unchanged) ---
class ListenerStartRequest(BaseModel):
    port: int

# --- Admin Schemas ---
class UserInVersionResponse(AppBaseModel):
    username: str

class Hl7VersionResponse(AppBaseModel):
    id: int
    version: str
    description: Optional[str] = None
    is_active: bool
    is_default: bool # <-- ADD THIS
    processed_at: datetime
    user: UserInVersionResponse = Field(exclude=True) 

    @computed_field
    @property
    def processed_by(self) -> str:
        return self.user.username if self.user else 'Unknown'

# --- Terminology Schemas (unchanged) ---
class DefinitionBase(AppBaseModel):
    table_id: str = Field(..., max_length=10)
    value: str = Field(..., max_length=100)
    description: str = Field(..., max_length=255)

class DefinitionCreate(DefinitionBase):
    pass

class DefinitionUpdate(BaseModel):
    value: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)

class Hl7TableDefinitionResponse(DefinitionBase):
    id: int
    
# --- NEW/UPDATED SCHEMAS FOR SIMULATOR ---

# --- Endpoint (formerly Hl7Destination) ---
class EndpointBase(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    endpoint_type: str = Field(..., pattern=r'^(MLLP|DICOM_SCP)$')
    hostname: str
    port: int
    ae_title: Optional[str] = Field(None, max_length=64)
    aet_title: Optional[str] = Field(None, max_length=64)

class EndpointCreate(EndpointBase):
    pass

class EndpointUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    endpoint_type: Optional[str] = Field(None, pattern=r'^(MLLP|DICOM_SCP)$')
    hostname: Optional[str] = None
    port: Optional[int] = None
    ae_title: Optional[str] = Field(None, max_length=64)
    aet_title: Optional[str] = Field(None, max_length=64)

class EndpointResponse(EndpointBase):
    id: int
    user_id: int

# --- Generator Template ---
class GeneratorTemplateBase(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    message_type: str = Field(..., max_length=50)
    content: str

class GeneratorTemplateCreate(GeneratorTemplateBase):
    pass

class GeneratorTemplateResponse(GeneratorTemplateBase):
    id: int
    user_id: int
    created_at: datetime

# --- Simulation Step ---
class SimulationStepBase(AppBaseModel):
    step_order: int
    step_type: str
    parameters: Dict[str, Any]

class SimulationStepCreate(SimulationStepBase):
    pass

class SimulationStepResponse(SimulationStepBase):
    id: int

# --- Simulation Template ---
class SimulationTemplateBase(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class SimulationTemplateCreate(SimulationTemplateBase):
    steps: List[SimulationStepCreate]

class SimulationTemplateResponse(SimulationTemplateBase):
    id: int
    user_id: int
    created_at: datetime
    steps: List[SimulationStepResponse]

class SimulationTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    steps: Optional[List[SimulationStepCreate]] = None

# --- Simulation Run ---
class SimulationRunCreate(BaseModel):
    template_id: int
    # --- ADD THIS FIELD ---
    patient_count: int = Field(1, gt=0) # Default to 1, must be greater than 0

class SimulationRunEventResponse(AppBaseModel):
    id: int
    timestamp: datetime
    step_order: int
    iteration: int
    status: str
    details: str

class SimulationRunResponse(AppBaseModel):
    id: int
    user_id: int
    template_id: int
    # --- ADD THIS FIELD ---
    patient_count: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    events: List[SimulationRunEventResponse]


# --- END OF FILE app/schemas.py ---