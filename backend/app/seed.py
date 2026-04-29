"""Bootstrap the DB and create the initial admin user.

Usage:  python -m app.seed
"""
from __future__ import annotations

from app.auth.passwords import hash_password
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.domain.enums import Role
from app.models.user import User
from app.repositories import users as users_repo


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = users_repo.get_by_username(db, settings.seed_admin_username)
        if existing:
            print(f"Admin '{settings.seed_admin_username}' already exists.")
            return
        admin = User(
            username=settings.seed_admin_username,
            email=settings.seed_admin_email,
            password_hash=hash_password(settings.seed_admin_password),
            role=Role.admin.value,
        )
        users_repo.create(db, admin)
        print(f"Created admin '{admin.username}'.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
