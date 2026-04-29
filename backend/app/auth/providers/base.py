"""Auth provider interface.

Implementations return the local `User` row for a successfully authenticated
principal, or `None` otherwise. External providers (LDAP/AD/OIDC) will
typically JIT-provision a local `User` on first successful auth.
"""
from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.models.user import User


class AuthProvider(Protocol):
    name: str

    def authenticate(self, db: Session, username: str, password: str) -> User | None: ...
