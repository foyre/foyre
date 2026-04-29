"""Shared FastAPI dependencies: DB session, current user, role guards.

All role checks funnel through `require_role(...)` so authorization rules
live in one place.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import service as auth
from app.db import get_db
from app.domain.enums import Role
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_UNAUTH_HEADERS = {"WWW-Authenticate": "Bearer"}


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "not authenticated", headers=_UNAUTH_HEADERS
        )
    user = auth.resolve_user(db, token)
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid or expired token", headers=_UNAUTH_HEADERS
        )
    return user


def require_role(*allowed: Role):
    """Dependency factory: reject users whose role isn't in `allowed`."""

    def _guard(user: User = Depends(get_current_user)) -> User:
        if Role(user.role) not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return user

    return _guard
