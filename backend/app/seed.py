"""Bootstrap the DB and create the initial admin user.

Usage:  python -m app.seed
"""
from __future__ import annotations

from app.auth.passwords import hash_password
from app.config import INSECURE_SEED_PASSWORDS, is_production_env, settings
from app.db import Base, SessionLocal, engine
from app.domain.enums import Role
from app.models.user import User
from app.repositories import users as users_repo


def _enforce_seed_password() -> None:
    """Refuse to create the seed admin with a known-insecure password.

    This check lives here (and not in `app.config`) because only the one-shot
    seed Job is given `SEED_ADMIN_PASSWORD`; running it at import-time would
    crash the main API pod, which doesn't need this value.
    """
    if not is_production_env(settings):
        return
    if settings.seed_admin_password in INSECURE_SEED_PASSWORDS:
        raise RuntimeError(
            "Refusing to seed the initial admin with a known-insecure "
            f"password ({settings.seed_admin_password!r}) in APP_ENV="
            f"{settings.app_env!r}. Set SEED_ADMIN_PASSWORD to a strong "
            "value (e.g. via the chart's --set-string seed.admin.password=...)."
        )


def run() -> None:
    _enforce_seed_password()
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
            # Force the seeded admin to set their own password on first login.
            # The chart and quickstart pass a password that the operator chose,
            # but we still want to ensure that password isn't reused long-term.
            must_change_password=True,
        )
        users_repo.create(db, admin)
        print(f"Created admin '{admin.username}'.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
