# backend/app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# User-related schemas
class UserBase(BaseModel):
    username: str = Field(..., max_length=32)
    email: Optional[EmailStr] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserOut(UserBase):
    id: int
    created_at: datetime
    class Config:
        orm_mode = True

# Auth
class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# For simplicity, we use UserOut for /auth/me responses (could create separate schema if needed)
