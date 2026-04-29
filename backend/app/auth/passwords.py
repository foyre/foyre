"""Password hashing.

Uses the `bcrypt` library directly. Keeping this isolated so the algorithm
(cost factor, future migration to argon2, pepper, etc.) can change in one place.

bcrypt operates on at most 72 bytes of input; we enforce that at the boundary
so failures are explicit rather than silently truncated.
"""
from __future__ import annotations

import bcrypt

_BCRYPT_MAX_BYTES = 72


class PasswordTooLong(ValueError):
    pass


def _as_bytes(plain: str) -> bytes:
    data = plain.encode("utf-8")
    if len(data) > _BCRYPT_MAX_BYTES:
        raise PasswordTooLong(
            f"password exceeds {_BCRYPT_MAX_BYTES} bytes (bcrypt limit)"
        )
    return data


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_as_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_as_bytes(plain), hashed.encode("utf-8"))
    except (PasswordTooLong, ValueError):
        return False
