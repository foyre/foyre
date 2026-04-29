"""Local username/password auth provider.

Authenticates against user rows stored in the Foyre database. Alternative
providers (LDAP, AD, OIDC) can be added as siblings implementing the same
`AuthProvider` interface.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.passwords import verify_password
from app.models.user import User
from app.repositories import users as users_repo


class LocalAuthProvider:
    name = "local"

    def authenticate(self, db: Session, username: str, password: str) -> User | None:
        user = users_repo.get_by_username(db, username)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
