"""Thin DB access for validation ingest staging records."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.validation_ingest_record import ValidationIngestRecord


def save(db: Session, row: ValidationIngestRecord) -> ValidationIngestRecord:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def latest_for_step(
    db: Session, run_id: int, step_name: str
) -> ValidationIngestRecord | None:
    """Most recent upload for a (run, step) — what the runner reads when
    finalizing the step."""
    stmt = (
        select(ValidationIngestRecord)
        .where(
            ValidationIngestRecord.validation_run_id == run_id,
            ValidationIngestRecord.step_name == step_name,
        )
        .order_by(ValidationIngestRecord.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()
