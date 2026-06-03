"""Validation ingest endpoint — called by a job's uploader sidecar.

Authenticated ONLY by a per-run ingest token (not a user bearer). The
token is scoped to a single (run, step); the path `run_id` must match the
token's subject. This endpoint never accepts a normal user token, and the
ingest token can't be used as a user token (different scope).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.validation_ingest import IngestRequest, IngestResult
from app.services import validation_ingest_service
from app.validation.ingest_token import verify_ingest_token

router = APIRouter()


def _claims_from_header(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "missing ingest token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    claims = verify_ingest_token(token)
    if claims is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "invalid or expired ingest token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


@router.post("/{run_id}", response_model=IngestResult)
def ingest(
    run_id: int,
    body: IngestRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    claims = _claims_from_header(authorization)
    # The token's subject must match the run it's uploading to.
    if str(claims.get("sub")) != str(run_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "token is not scoped to this run"
        )

    summary = validation_ingest_service.ingest(
        db,
        run_id=run_id,
        step_name=claims.get("step") or "",
        step_result_id=claims.get("srid"),
        body=body.model_dump(mode="python"),
    )
    return IngestResult(
        stored=summary.stored,
        omitted=summary.omitted,
        record_id=summary.record_id,
    )
