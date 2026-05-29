"""Intake request orchestration.

Owns:
  - ownership + role-scoped listing
  - draft create / update
  - submit (runs risk evaluation, records history)
  - status transitions (delegates to workflow_service for rules)

Routes call this module; they never touch repositories or models directly.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.domain.enums import PRIVILEGED_ROLES, HistoryEventType, RequestStatus, Role
from app.models.request import IntakeRequest
from app.models.user import User
from app.repositories import requests as requests_repo
from app.schemas.request import IntakePayload
from app.services import (
    form_schema_service,
    history_service,
    risk_service,
    validation_approval_service,
    workflow_service,
)


def _owns_or_privileged(user: User, req: IntakeRequest) -> bool:
    return req.created_by_id == user.id or Role(user.role) in PRIVILEGED_ROLES


def get_authorized(db: Session, user: User, request_id: int) -> IntakeRequest:
    req = requests_repo.get(db, request_id)
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    if not _owns_or_privileged(user, req):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized for this request")
    return req


def list_visible(db: Session, user: User) -> list[IntakeRequest]:
    if Role(user.role) in PRIVILEGED_ROLES:
        return requests_repo.list_all(db)
    return requests_repo.list_for_owner(db, user.id)


def create_draft(db: Session, user: User, payload: dict) -> IntakeRequest:
    req = requests_repo.save(
        db,
        IntakeRequest(created_by_id=user.id, status=RequestStatus.draft.value, payload=payload),
    )
    history_service.record_event(
        db, request_id=req.id, actor_id=user.id, event_type=HistoryEventType.created
    )
    return req


def update_draft(db: Session, user: User, req: IntakeRequest, payload: dict) -> IntakeRequest:
    if req.created_by_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the owner can edit a draft")
    if RequestStatus(req.status) != RequestStatus.draft:
        raise HTTPException(status.HTTP_409_CONFLICT, "only drafts can be edited")
    req.payload = payload
    req = requests_repo.save(db, req)
    history_service.record_event(
        db, request_id=req.id, actor_id=user.id, event_type=HistoryEventType.updated
    )
    return req


def submit(db: Session, user: User, req: IntakeRequest) -> IntakeRequest:
    if req.created_by_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the owner can submit")
    try:
        workflow_service.assert_transition(
            RequestStatus(req.status), Role(user.role), RequestStatus.submitted
        )
    except workflow_service.TransitionNotAllowed as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    try:
        validated = IntakePayload.model_validate(req.payload)
    except ValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "payload is incomplete or invalid", "errors": e.errors()},
        )
    custom_errors = form_schema_service.validate_custom_payload(db, req.payload)
    if custom_errors["errors"]:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "payload is incomplete or invalid",
                "errors": custom_errors["errors"],
            },
        )
    level, reasons = risk_service.derive_risk(validated)
    req.status = RequestStatus.submitted.value
    req.risk_level = level.value
    req.risk_reasons = reasons
    req = requests_repo.save(db, req)
    history_service.record_event(
        db, request_id=req.id, actor_id=user.id, event_type=HistoryEventType.submitted
    )
    history_service.record_event(
        db,
        request_id=req.id,
        actor_id=user.id,
        event_type=HistoryEventType.risk_evaluated,
        detail={"level": level.value, "reasons": reasons},
    )
    return req


def change_status(
    db: Session,
    user: User,
    req: IntakeRequest,
    new_status: RequestStatus,
    *,
    override_validation: bool = False,
    override_reason: str | None = None,
) -> IntakeRequest:
    try:
        workflow_service.assert_transition(
            RequestStatus(req.status), Role(user.role), new_status
        )
    except workflow_service.TransitionNotAllowed as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    # Validation approval gate: only relevant when approving.
    if new_status == RequestStatus.approved:
        _enforce_validation_gate(
            db, user, req, override_validation=override_validation, override_reason=override_reason
        )

    from_status = req.status
    req.status = new_status.value
    req = requests_repo.save(db, req)
    history_service.record_event(
        db,
        request_id=req.id,
        actor_id=user.id,
        event_type=HistoryEventType.status_changed,
        detail={"from": from_status, "to": new_status.value},
    )
    return req


def _enforce_validation_gate(
    db: Session,
    user: User,
    req: IntakeRequest,
    *,
    override_validation: bool,
    override_reason: str | None,
) -> None:
    """Block (or override) approval based on the latest validation run.

    Records `validation_approval_blocked` when an approval is refused and
    `validation_override_used` when a reviewer overrides a blocked gate.
    """
    gate = validation_approval_service.evaluate(db, req.id)
    if not gate.blocked:
        return

    if not override_validation:
        history_service.record_event(
            db,
            request_id=req.id,
            actor_id=user.id,
            event_type=HistoryEventType.validation_approval_blocked,
            detail={
                "reason": gate.reason,
                "impact": gate.impact.value,
                "latest_run_id": gate.latest_run.id if gate.latest_run else None,
            },
        )
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "message": gate.reason or "Approval is blocked by validation policy.",
                "approval_impact": gate.impact.value,
                "override_allowed": gate.override_allowed,
            },
        )

    # Override requested.
    if not gate.override_allowed:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "validation override is disabled by policy; approval cannot be overridden",
        )
    if not override_reason or not override_reason.strip():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "an override reason is required to approve past a blocking validation result",
        )
    history_service.record_event(
        db,
        request_id=req.id,
        actor_id=user.id,
        event_type=HistoryEventType.validation_override_used,
        detail={
            "reason": override_reason.strip(),
            "impact": gate.impact.value,
            "latest_run_id": gate.latest_run.id if gate.latest_run else None,
        },
    )
