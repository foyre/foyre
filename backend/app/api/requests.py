from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.domain.enums import RequestStatus
from app.models.user import User
from app.repositories import history as history_repo
from app.schemas.history import HistoryEventOut
from app.schemas.request import RequestCreate, RequestOut, RequestUpdate, StatusChange
from app.services import request_service

router = APIRouter()


@router.get("", response_model=list[RequestOut])
def list_requests(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return request_service.list_visible(db, user)


@router.post("", response_model=RequestOut, status_code=201)
def create_request(
    body: RequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return request_service.create_draft(db, user, body.payload)


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return request_service.get_authorized(db, user, request_id)


@router.patch("/{request_id}", response_model=RequestOut)
def update_request(
    request_id: int,
    body: RequestUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = request_service.get_authorized(db, user, request_id)
    return request_service.update_draft(db, user, req, body.payload)


@router.post("/{request_id}/submit", response_model=RequestOut)
def submit_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = request_service.get_authorized(db, user, request_id)
    return request_service.submit(db, user, req)


@router.post("/{request_id}/status", response_model=RequestOut)
def change_status(
    request_id: int,
    body: StatusChange,
    db: Session = Depends(get_db),
    # Any authenticated user can attempt a transition; the workflow table
    # (enforced via request_service → workflow_service) decides whether a
    # given (current_status, target, role) triple is allowed. Requesters use
    # this to mark their submitted requests as ready_for_review; reviewers use
    # it for the usual review-stage transitions. Owner-bound checks (e.g.
    # "you're acting on your own request") are layered on top when needed.
    user: User = Depends(get_current_user),
):
    req = request_service.get_authorized(db, user, request_id)
    # Requester-driven transitions (submitted↔ready_for_review) must be on
    # their own request — protect against another requester flipping yours.
    owner_only_transitions = {
        (RequestStatus.submitted, RequestStatus.ready_for_review),
        (RequestStatus.ready_for_review, RequestStatus.submitted),
    }
    if (RequestStatus(req.status), body.new_status) in owner_only_transitions:
        if req.created_by_id != user.id and user.role != "admin":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "only the request owner or an admin can mark ready/unready",
            )
    return request_service.change_status(db, user, req, body.new_status)


@router.get("/{request_id}/history", response_model=list[HistoryEventOut])
def get_history(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request_service.get_authorized(db, user, request_id)
    return history_repo.list_for_request(db, request_id)
