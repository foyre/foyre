"""Approval gate: does a request's validation state permit approval?

Pure-ish evaluation reused by both the approval hook (in
`request_service.change_status`) and a read-only endpoint the UI uses to
render the approve button + warnings.

Policy (from `validation_policy_service`):
  - require_validation_before_approval: if True, approval is blocked until
    a run has *completed* (passed / warning / failed). A still-running,
    errored, or never-run request is blocked.
  - block_approval_on_failed_validation: if True, a completed run whose
    approval_impact is `blocked` blocks approval.

`warning` impact never blocks; it's surfaced to the reviewer as advisory.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.enums import ApprovalImpact, ValidationRunStatus
from app.models.validation_run import ValidationRun
from app.repositories import validation_runs as runs_repo
from app.services import validation_policy_service

# Run statuses that count as "a validation actually completed".
_COMPLETED_STATUSES = {
    ValidationRunStatus.passed.value,
    ValidationRunStatus.warning.value,
    ValidationRunStatus.failed.value,
}


@dataclass(frozen=True)
class ApprovalGate:
    blocked: bool
    impact: ApprovalImpact
    reason: str | None
    latest_run: ValidationRun | None
    override_allowed: bool
    # True when there's no completed run yet (UI shows an advisory warning
    # even if `blocked` is False because the policy doesn't require it).
    missing_validation: bool


def evaluate(db: Session, request_id: int) -> ApprovalGate:
    policy = validation_policy_service.get_effective(db)
    latest = runs_repo.latest_for_request(db, request_id)

    completed = latest is not None and latest.status in _COMPLETED_STATUSES
    missing = not completed

    impact = ApprovalImpact.none
    if completed:
        try:
            impact = ApprovalImpact(latest.approval_impact)
        except ValueError:
            impact = ApprovalImpact.none

    blocked = False
    reason: str | None = None

    if policy.require_validation_before_approval and missing:
        blocked = True
        reason = "A completed validation run is required before this request can be approved."
    elif (
        completed
        and policy.block_approval_on_failed_validation
        and impact == ApprovalImpact.blocked
    ):
        blocked = True
        reason = (
            "The latest validation run has blocking failures. "
            "Resolve them or override with a reason."
        )

    return ApprovalGate(
        blocked=blocked,
        impact=impact,
        reason=reason,
        latest_run=latest,
        override_allowed=policy.allow_validation_override,
        missing_validation=missing,
    )
