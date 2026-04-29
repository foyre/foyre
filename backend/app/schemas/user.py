from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import Role


class UserRef(BaseModel):
    """Compact user reference embedded in other resources (owner, author, actor)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: Role
    is_active: bool
    must_change_password: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Role = Role.requester
    # Default True: admin-created users must rotate the temp password on first
    # login. Override to False only when an admin is creating themselves
    # directly and wants to choose the password.
    must_change_password: bool = True


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class UserUpdate(BaseModel):
    """Admin update of another user. All fields optional; only provided ones change."""

    role: Role | None = None
    is_active: bool | None = None
