"""Thin DB access for the single-row form schema config."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.form_schema_config import FormSchemaConfig


def get(db: Session) -> FormSchemaConfig | None:
    """Return the single config row, if it exists."""
    return db.execute(
        select(FormSchemaConfig).order_by(FormSchemaConfig.id.asc()).limit(1)
    ).scalar_one_or_none()


def save(db: Session, row: FormSchemaConfig) -> FormSchemaConfig:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: FormSchemaConfig) -> None:
    db.delete(row)
    db.commit()
