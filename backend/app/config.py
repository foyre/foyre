"""Application settings.

Loaded from environment / .env. Keep this small; add fields only when needed.
"""
from __future__ import annotations

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Known-insecure placeholders. We refuse to use these in any non-local env
# so an accidental `docker run` without env vars doesn't sign JWTs with
# "change-me" or seed admin/admin.
_INSECURE_JWT_DEFAULTS = {"", "change-me", "changeme", "secret"}
_INSECURE_SEED_PASSWORDS = {"admin", "password", "change-me", "CHANGE_ME_ON_FIRST_INSTALL"}


class Settings(BaseSettings):
    # local | dev | staging | production — anything other than 'local' is
    # treated as a real deployment and triggers strict checks below.
    app_env: str = "local"
    database_url: str = "sqlite:///./foyre.db"

    # Auth
    auth_provider: str = "local"  # local | ldap | ad | oidc (future)
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480

    # Fernet key for encrypting sensitive fields at rest (host kubeconfigs,
    # user kubeconfigs). Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # An empty / placeholder value disables features that require encryption.
    app_secret_key: str = ""

    # Seed / bootstrap
    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin"
    seed_admin_email: str = "admin@example.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def _enforce_production_secrets(s: Settings) -> None:
    """Refuse to boot in a non-local env if known-insecure defaults are in use."""
    if s.app_env.lower() in ("local", "dev", "development", "test"):
        if s.jwt_secret in _INSECURE_JWT_DEFAULTS:
            logger.warning(
                "JWT_SECRET is set to a known-insecure default (%r). "
                "OK for local dev; set a strong value before deploying.",
                s.jwt_secret,
            )
        return

    problems: list[str] = []
    if s.jwt_secret in _INSECURE_JWT_DEFAULTS:
        problems.append(
            f"JWT_SECRET is set to a known-insecure default ({s.jwt_secret!r}); "
            "generate one with `openssl rand -hex 32`."
        )
    if s.seed_admin_password in _INSECURE_SEED_PASSWORDS:
        problems.append(
            f"SEED_ADMIN_PASSWORD is set to a known-insecure default "
            f"({s.seed_admin_password!r}); choose a strong password."
        )
    if problems:
        raise RuntimeError(
            "Refusing to start with insecure defaults (APP_ENV="
            f"{s.app_env!r}):\n  - " + "\n  - ".join(problems)
        )


_enforce_production_secrets(settings)
