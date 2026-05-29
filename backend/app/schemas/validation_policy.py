"""DTOs for the validation approval policy + the approval-gate read view."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PolicyOut(BaseModel):
    require_validation_before_approval: bool
    block_approval_on_failed_validation: bool
    allow_validation_override: bool
    updated_at: datetime | None = None
    updated_by_id: int | None = None


class PolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_validation_before_approval: bool | None = None
    block_approval_on_failed_validation: bool | None = None
    allow_validation_override: bool | None = None


class ApprovalGateOut(BaseModel):
    """Read-only view the UI uses to render the approve button + warnings."""

    blocked: bool
    impact: str
    reason: str | None
    override_allowed: bool
    missing_validation: bool
    latest_run_id: int | None
