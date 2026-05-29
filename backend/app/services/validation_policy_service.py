"""Admin-tunable validation policy (single row) + effective-value resolution.

Mirrors `form_schema_service`'s single-row pattern: if no row exists,
callers get the model defaults. The three toggles gate how validation
results affect the approval transition.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.validation_policy_config import ValidationPolicyConfig
from app.repositories import validation_policy_configs as repo

# Defaults must match the column defaults on ValidationPolicyConfig.
_DEFAULTS = {
    "require_validation_before_approval": False,
    "block_approval_on_failed_validation": True,
    "allow_validation_override": True,
}


@dataclass(frozen=True)
class EffectivePolicy:
    require_validation_before_approval: bool
    block_approval_on_failed_validation: bool
    allow_validation_override: bool


def get_config(db: Session) -> ValidationPolicyConfig | None:
    return repo.get(db)


def get_effective(db: Session) -> EffectivePolicy:
    row = repo.get(db)
    if row is None:
        return EffectivePolicy(**_DEFAULTS)
    return EffectivePolicy(
        require_validation_before_approval=row.require_validation_before_approval,
        block_approval_on_failed_validation=row.block_approval_on_failed_validation,
        allow_validation_override=row.allow_validation_override,
    )


def update(
    db: Session,
    user: User,
    *,
    require_validation_before_approval: bool | None = None,
    block_approval_on_failed_validation: bool | None = None,
    allow_validation_override: bool | None = None,
) -> ValidationPolicyConfig:
    """Upsert the single policy row, leaving unspecified fields unchanged."""
    row = repo.get(db)
    if row is None:
        row = ValidationPolicyConfig(**_DEFAULTS)
    if require_validation_before_approval is not None:
        row.require_validation_before_approval = require_validation_before_approval
    if block_approval_on_failed_validation is not None:
        row.block_approval_on_failed_validation = block_approval_on_failed_validation
    if allow_validation_override is not None:
        row.allow_validation_override = allow_validation_override
    row.updated_by_id = user.id
    return repo.save(db, row)
