"""Authentication request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    """User login payload."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    """Refresh-token rotation payload."""

    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    """Logout payload."""

    refresh_token: str = Field(min_length=32)


class TokenResponse(BaseModel):
    """JWT response envelope."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    user: UserRead

