"""Per-run ingest tokens for the uploader sidecar.

A validation job's uploader sidecar needs to POST results + artifacts back
to the Foyre API, but it must NOT carry a user's bearer token. Instead the
runner mints a short-lived, signed token scoped to a single (run, step)
and injects it into the sidecar. The ingest endpoint accepts only this
token type.

Signed with the same `JWT_SECRET` as user tokens but carries a distinct
`scope` so the two can never be confused — a user token can't hit the
ingest endpoint and an ingest token can't authenticate as a user.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import settings

SCOPE = "validation-ingest"


def issue_ingest_token(
    run_id: int,
    step_name: str,
    step_result_id: int | None = None,
    ttl_minutes: int | None = None,
) -> str:
    now = datetime.now(tz=timezone.utc)
    ttl = ttl_minutes or settings.validation_ingest_token_minutes
    payload: dict[str, Any] = {
        "sub": str(run_id),
        "scope": SCOPE,
        "step": step_name,
        "srid": step_result_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_ingest_token(token: str) -> dict[str, Any] | None:
    """Return the claims for a valid ingest token, else None.

    Rejects (returns None) on bad signature, expiry, or wrong scope — so a
    user access token is not accepted here.
    """
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if claims.get("scope") != SCOPE:
        return None
    if claims.get("sub") is None:
        return None
    return claims
