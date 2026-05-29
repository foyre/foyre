"""Thin DB access for validation runs."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.validation_run import ValidationRun


def get(db: Session, id_: int) -> ValidationRun | None:
    return db.get(ValidationRun, id_)


def list_for_request(db: Session, request_id: int) -> list[ValidationRun]:
    """Return all runs for a request, newest first (most relevant on top)."""
    stmt = (
        select(ValidationRun)
        .where(ValidationRun.request_id == request_id)
        .order_by(ValidationRun.id.desc())
    )
    return list(db.execute(stmt).scalars())


def latest_for_request(db: Session, request_id: int) -> ValidationRun | None:
    """The most recently started run for a request, regardless of status.

    Used by the approval gate to look up "the run we should consider
    when deciding whether to allow this approval".
    """
    stmt = (
        select(ValidationRun)
        .where(ValidationRun.request_id == request_id)
        .order_by(ValidationRun.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def save(db: Session, row: ValidationRun) -> ValidationRun:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
