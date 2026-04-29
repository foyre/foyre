"""Application settings.

Loaded from environment / .env. Keep this small; add fields only when needed.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
