"""Authentication service.

Two module-level functions plus a module-level `_provider`. Route handlers and
dependencies import `login` / `resolve_user` and never construct anything.

Adding LDAP/AD/OIDC later means:
  1. Add a new provider module in `app/auth/providers/` implementing the
     `AuthProvider` protocol.
  2. Add one branch in `_build_provider` below.
  3. Flip `AUTH_PROVIDER` in config.
No routes or services change.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.providers.base import AuthProvider
from app.auth.providers.local import LocalAuthProvider
from app.auth.tokens import decode_token, issue_token
from app.config import settings
from app.models.user import User
from app.repositories import users as users_repo


def _build_provider() -> AuthProvider:
    match settings.auth_provider:
        case "local":
            return LocalAuthProvider()
        # case "ldap": return LdapAuthProvider()   # future
        # case "ad":   return AdAuthProvider()     # future
        # case "oidc": return OidcAuthProvider()   # future
        case _:
            raise RuntimeError(f"Unsupported AUTH_PROVIDER: {settings.auth_provider}")


# Chosen once at import time. The provider object is stateless for the local
# case; for external providers any per-request state should live in the
# provider itself or be passed via `db`.
_provider: AuthProvider = _build_provider()


def login(db: Session, username: str, password: str) -> tuple[User, str] | None:
    """Authenticate against the configured provider and issue a token."""
    user = _provider.authenticate(db, username, password)
    if not user:
        return None
    token = issue_token(subject=str(user.id), extra={"role": user.role})
    return user, token


def resolve_user(db: Session, token: str) -> User | None:
    """Return the local `User` identified by a bearer token, or `None`."""
    claims = decode_token(token)
    if not claims:
        return None
    sub = claims.get("sub")
    if not sub:
        return None
    user = users_repo.get_by_id(db, int(sub))
    if not user or not user.is_active:
        return None
    return user
