"""DB access for validation environments."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.validation_environment import ValidationEnvironment


def get(db: Session, id_: int) -> ValidationEnvironment | None:
    return db.get(ValidationEnvironment, id_)


def current_for_request(
    db: Session, request_id: int
) -> ValidationEnvironment | None:
    """Most-recent non-torn-down environment for a request, if any."""
    stmt = (
        select(ValidationEnvironment)
        .where(ValidationEnvironment.request_id == request_id)
        .where(ValidationEnvironment.status != "torn_down")
        .order_by(ValidationEnvironment.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def save(db: Session, row: ValidationEnvironment) -> ValidationEnvironment:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
