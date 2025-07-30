# --- START OF FILE app/schemas.py ---
from pydantic import BaseModel, Field, EmailStr, computed_field
from typing import List, Optional
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
    processed_at: datetime
    user: UserInVersionResponse = Field(exclude=True) 

    @computed_field
    @property
    def processed_by(self) -> str:
        return self.user.username if self.user else 'Unknown'

# --- NEW TERMINOLOGY SCHEMAS ---
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

# --- END OF FILE app/schemas.py ---