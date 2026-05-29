"""Thin DB access for validation step results."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.validation_step_result import ValidationStepResult


def get(db: Session, id_: int) -> ValidationStepResult | None:
    return db.get(ValidationStepResult, id_)


def list_for_run(db: Session, run_id: int) -> list[ValidationStepResult]:
    stmt = (
        select(ValidationStepResult)
        .where(ValidationStepResult.validation_run_id == run_id)
        .order_by(ValidationStepResult.sort_order.asc(), ValidationStepResult.id.asc())
    )
    return list(db.execute(stmt).scalars())


def get_by_step_name(
    db: Session, run_id: int, step_name: str
) -> ValidationStepResult | None:
    """Lookup helper for downstream steps that consume an upstream's
    results (e.g., `kubernetes_security` reading `workload_inventory`'s
    artifact)."""
    stmt = select(ValidationStepResult).where(
        ValidationStepResult.validation_run_id == run_id,
        ValidationStepResult.step_name == step_name,
    )
    return db.execute(stmt).scalar_one_or_none()


def save(db: Session, row: ValidationStepResult) -> ValidationStepResult:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
