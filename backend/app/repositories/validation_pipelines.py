"""Thin DB access for validation pipelines."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.validation_pipeline import ValidationPipeline


def get(db: Session, id_: int) -> ValidationPipeline | None:
    return db.get(ValidationPipeline, id_)


def get_by_name(db: Session, name: str) -> ValidationPipeline | None:
    return db.execute(
        select(ValidationPipeline).where(ValidationPipeline.name == name)
    ).scalar_one_or_none()


def get_default(db: Session) -> ValidationPipeline | None:
    return db.execute(
        select(ValidationPipeline)
        .where(ValidationPipeline.is_default.is_(True))
        .limit(1)
    ).scalar_one_or_none()


def list_all(db: Session) -> list[ValidationPipeline]:
    stmt = select(ValidationPipeline).order_by(ValidationPipeline.id.asc())
    return list(db.execute(stmt).scalars())


def list_enabled(db: Session) -> list[ValidationPipeline]:
    stmt = (
        select(ValidationPipeline)
        .where(ValidationPipeline.enabled.is_(True))
        .order_by(ValidationPipeline.id.asc())
    )
    return list(db.execute(stmt).scalars())


def save(db: Session, row: ValidationPipeline) -> ValidationPipeline:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: ValidationPipeline) -> None:
    db.delete(row)
    db.commit()


def clear_other_defaults(db: Session, keep_id: int | None) -> None:
    """Only one pipeline may be marked default at a time. Mirrors
    `host_clusters.clear_other_defaults`.
    """
    for row in list_all(db):
        if row.is_default and row.id != keep_id:
            row.is_default = False
            db.add(row)
    db.commit()
