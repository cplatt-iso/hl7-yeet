# --- START OF FILE app/schemas.py ---
from pydantic import BaseModel, Field, EmailStr
from typing import List

# --- Pydantic Config ---
# This little bit of magic tells Pydantic it's okay to create schemas from ORM objects.
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

# --- END OF FILE app/schemas.py ---