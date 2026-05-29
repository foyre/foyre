"""Admin endpoints for the validation approval policy (single row)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_role
from app.domain.enums import Role
from app.models.user import User
from app.schemas.validation_policy import PolicyOut, PolicyUpdate
from app.services import validation_policy_service as svc

router = APIRouter()


def _to_out(db: Session) -> PolicyOut:
    eff = svc.get_effective(db)
    row = svc.get_config(db)
    return PolicyOut(
        require_validation_before_approval=eff.require_validation_before_approval,
        block_approval_on_failed_validation=eff.block_approval_on_failed_validation,
        allow_validation_override=eff.allow_validation_override,
        updated_at=row.updated_at if row else None,
        updated_by_id=row.updated_by_id if row else None,
    )


@router.get("", response_model=PolicyOut)
def get_policy(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    return _to_out(db)


@router.put("", response_model=PolicyOut)
def update_policy(
    body: PolicyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.admin)),
):
    svc.update(
        db,
        user,
        require_validation_before_approval=body.require_validation_before_approval,
        block_approval_on_failed_validation=body.block_approval_on_failed_validation,
        allow_validation_override=body.allow_validation_override,
    )
    return _to_out(db)
