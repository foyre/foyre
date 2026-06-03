"""Application settings.

Loaded from environment / .env. Keep this small; add fields only when needed.
"""
from __future__ import annotations

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Known-insecure placeholders. We refuse to boot the main app in any non-local
# env if `JWT_SECRET` matches one of these — that secret is required by every
# process and a placeholder would silently sign forgeable tokens.
#
# `SEED_ADMIN_PASSWORD` is validated separately in `app.seed`, NOT here: the
# main app deliberately has no `SEED_ADMIN_PASSWORD` env var (it doesn't need
# one), so checking it at module-import time would crash the API pod on a
# value that's only relevant to the one-shot seed Job.
_INSECURE_JWT_DEFAULTS = {"", "change-me", "changeme", "secret"}
INSECURE_SEED_PASSWORDS = {
    "admin",
    "password",
    "change-me",
    "CHANGE_ME_ON_FIRST_INSTALL",
}


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

    # TTL for per-run validation ingest tokens (handed to the uploader
    # sidecar). Short by design — a single job's lifetime.
    validation_ingest_token_minutes: int = 60

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


def is_production_env(s: Settings) -> bool:
    """True iff this process is running in a real (non-local) environment."""
    return s.app_env.lower() not in ("local", "dev", "development", "test")


def _enforce_production_secrets(s: Settings) -> None:
    """Refuse to boot in a non-local env if JWT_SECRET is a known-insecure default.

    Only checks values that every process actually needs — i.e. `JWT_SECRET`.
    `SEED_ADMIN_PASSWORD` is checked in `app.seed`, not here.
    """
    if not is_production_env(s):
        if s.jwt_secret in _INSECURE_JWT_DEFAULTS:
            logger.warning(
                "JWT_SECRET is set to a known-insecure default (%r). "
                "OK for local dev; set a strong value before deploying.",
                s.jwt_secret,
            )
        return

    if s.jwt_secret in _INSECURE_JWT_DEFAULTS:
        raise RuntimeError(
            f"Refusing to start with insecure defaults (APP_ENV={s.app_env!r}):\n"
            f"  - JWT_SECRET is set to a known-insecure default ({s.jwt_secret!r}); "
            "generate one with `openssl rand -hex 32`."
        )


_enforce_production_secrets(settings)
