"""Symmetric encryption for sensitive fields stored at rest.

Used for host-cluster kubeconfigs and (later) user-facing vcluster kubeconfigs.
Isolated in this module so swapping to Vault / cloud KMS later is a local change.

`APP_SECRET_KEY` in config must be a 32-byte url-safe-base64 Fernet key. Generate:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class EncryptionNotConfigured(RuntimeError):
    """APP_SECRET_KEY is missing or unusable."""


def _fernet() -> Fernet:
    key = settings.app_secret_key
    if not key or key == "change-me-to-a-fernet-key":
        raise EncryptionNotConfigured(
            "APP_SECRET_KEY is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`"
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as e:
        raise EncryptionNotConfigured(f"APP_SECRET_KEY is not a valid Fernet key: {e}")


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt(token: bytes) -> str:
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken as e:
        raise EncryptionNotConfigured(
            "Encrypted value could not be decrypted. Has APP_SECRET_KEY changed?"
        ) from e


def is_configured() -> bool:
    try:
        _fernet()
        return True
    except EncryptionNotConfigured:
        return False
