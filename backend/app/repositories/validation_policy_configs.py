"""Thin DB access for the single-row validation policy config.

Mirrors `form_schema_configs` repository: at most one row exists; if
none does, callers fall back to the model defaults declared on
`ValidationPolicyConfig` itself.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.validation_policy_config import ValidationPolicyConfig


def get(db: Session) -> ValidationPolicyConfig | None:
    return db.execute(
        select(ValidationPolicyConfig)
        .order_by(ValidationPolicyConfig.id.asc())
        .limit(1)
    ).scalar_one_or_none()


def save(db: Session, row: ValidationPolicyConfig) -> ValidationPolicyConfig:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
