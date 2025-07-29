# --- START OF FILE app/schemas.py ---
from pydantic import BaseModel, Field, EmailStr, computed_field
from typing import List, Optional
from datetime import datetime

# --- Pydantic Config ---
class AppBaseModel(BaseModel):
    class Config:
        from_attributes = True

# --- Auth Schemas ---
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

# --- Template Schemas ---
class TemplateBase(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)

class TemplateCreate(TemplateBase):
    pass

class Template(TemplateBase):
    id: int

# --- API Data Schemas ---
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

# --- Listener Schemas ---
class ListenerStartRequest(BaseModel):
    port: int

# --- Admin Schemas ---

# --- THIS IS THE FIX (PART 1) ---
# A simple schema to represent the User object when it's nested.
# Pydantic will use this to correctly validate the nested ORM object.
class UserInVersionResponse(AppBaseModel):
    username: str

# --- THIS IS THE FIX (PART 2) ---
class Hl7VersionResponse(AppBaseModel):
    id: int
    version: str
    description: Optional[str] = None
    is_active: bool
    processed_at: datetime
    
    # We now tell Pydantic to expect a User object that conforms to our new schema.
    # It will be validated but not included in the final JSON output.
    user: UserInVersionResponse = Field(exclude=True) 

    @computed_field
    @property
    def processed_by(self) -> str:
        """Computes the 'processed_by' field from the validated, nested user object."""
        # Because 'self.user' is now a validated Pydantic model,
        # we can access its attributes directly.
        return self.user.username if self.user else 'Unknown'

# --- END OF FILE app/schemas.py ---