"""Pydantic schemas — Authentication."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserInfo


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
