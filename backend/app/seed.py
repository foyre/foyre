"""Bootstrap the DB, create the initial admin user, and seed defaults.

Usage:  python -m app.seed

Idempotent: safe to run on every deploy. Creates the admin user if it
doesn't exist and seeds the default validation pipeline if no pipeline
with its canonical name exists yet.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.passwords import hash_password
from app.config import INSECURE_SEED_PASSWORDS, is_production_env, settings
from app.db import Base, SessionLocal, engine
from app.domain.default_pipeline import DEFAULT_PIPELINE_NAME, DEFAULT_PIPELINE_YAML
from app.domain.enums import Role
from app.models.user import User
from app.models.validation_pipeline import ValidationPipeline
from app.repositories import users as users_repo
from app.repositories import validation_pipelines as pipelines_repo
from app.services import validation_pipeline_service


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


def _seed_admin(db: Session) -> User:
    """Create the initial admin if absent; return it either way."""
    existing = users_repo.get_by_username(db, settings.seed_admin_username)
    if existing:
        print(f"Admin '{settings.seed_admin_username}' already exists.")
        return existing
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
    return admin


def _seed_default_pipeline(db: Session, admin: User | None) -> None:
    """Seed the built-in default validation pipeline if it doesn't exist.

    Idempotent on the pipeline's canonical name so re-running the seed job
    never duplicates or overwrites an admin's edits to it. Marked as the
    default only when no other default pipeline is already configured.
    """
    if pipelines_repo.get_by_name(db, DEFAULT_PIPELINE_NAME):
        print(f"Pipeline '{DEFAULT_PIPELINE_NAME}' already exists.")
        return

    # Validate the shipped YAML through the same parser admins use, so a
    # malformed default fails loudly at seed time rather than at run time.
    normalized = validation_pipeline_service.parse_and_validate(DEFAULT_PIPELINE_YAML)

    make_default = pipelines_repo.get_default(db) is None
    pipeline = ValidationPipeline(
        name=normalized["name"],
        display_name=normalized["displayName"],
        description=normalized.get("description"),
        enabled=True,
        is_default=make_default,
        version=1,
        default_failure_policy=normalized["failurePolicy"],
        definition_yaml=DEFAULT_PIPELINE_YAML,
        definition_json=normalized,
        created_by_id=admin.id if admin else None,
        updated_by_id=admin.id if admin else None,
    )
    pipelines_repo.save(db, pipeline)
    print(
        f"Seeded default pipeline '{pipeline.name}'"
        + (" (marked default)." if make_default else ".")
    )


def run() -> None:
    _enforce_seed_password()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = _seed_admin(db)
        _seed_default_pipeline(db, admin)
    finally:
        db.close()


if __name__ == "__main__":
    run()
