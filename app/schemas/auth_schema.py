from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    business_name: str
    business_type: Optional[str] = None
    phone_number: str
    role: Optional[str] = "owner"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    business_id: UUID
    name: str
    email: str
    role: str


class UserResponse(BaseModel):
    id: UUID
    business_id: UUID
    name: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True
