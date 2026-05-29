"""Thin DB access for validation artifacts.

Artifact bytes live in a `LargeBinary` column (per product decision:
DB blobs). All read paths must go through this module so a future
"big artifact → filesystem" tier can be introduced in one place.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.validation_artifact import ValidationArtifact


def get(db: Session, id_: int) -> ValidationArtifact | None:
    return db.get(ValidationArtifact, id_)


def list_for_run(db: Session, run_id: int) -> list[ValidationArtifact]:
    stmt = (
        select(ValidationArtifact)
        .where(ValidationArtifact.validation_run_id == run_id)
        .order_by(ValidationArtifact.id.asc())
    )
    return list(db.execute(stmt).scalars())


def list_for_step_result(
    db: Session, step_result_id: int
) -> list[ValidationArtifact]:
    stmt = (
        select(ValidationArtifact)
        .where(ValidationArtifact.step_result_id == step_result_id)
        .order_by(ValidationArtifact.id.asc())
    )
    return list(db.execute(stmt).scalars())


def save(db: Session, row: ValidationArtifact) -> ValidationArtifact:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def read_bytes(row: ValidationArtifact) -> bytes:
    """Return raw artifact content. Indirection point for a future
    filesystem-backed tier; today it just returns `row.content`."""
    return row.content
