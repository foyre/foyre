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
from app.services import history_service, risk_service, workflow_service


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
    db: Session, user: User, req: IntakeRequest, new_status: RequestStatus
) -> IntakeRequest:
    try:
        workflow_service.assert_transition(
            RequestStatus(req.status), Role(user.role), new_status
        )
    except workflow_service.TransitionNotAllowed as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
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
