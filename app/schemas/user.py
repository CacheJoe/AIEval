"""User schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserBase(BaseModel):
    """Shared user fields."""

    email: EmailStr
    name: str = Field(min_length=2, max_length=150)
    role: UserRole
    is_active: bool = True


class UserCreate(UserBase):
    """User creation payload."""

    password: str = Field(min_length=8, max_length=128)


class UserStatusUpdate(BaseModel):
    """Toggle user activation."""

    is_active: bool


class UserRead(UserBase):
    """Public user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime

