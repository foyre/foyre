from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.domain.enums import PRIVILEGED_ROLES
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentOut
from app.services import comment_service, request_service

router = APIRouter()


@router.get("/{request_id}/comments", response_model=list[CommentOut])
def list_comments(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Listing is visible to anyone who can see the request (owner or privileged).
    request_service.get_authorized(db, user, request_id)
    return comment_service.list_comments(db, request_id)


@router.post("/{request_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    request_id: int,
    body: CommentCreate,
    db: Session = Depends(get_db),
    # Only reviewer / architect / admin may post comments.
    user: User = Depends(require_role(*PRIVILEGED_ROLES)),
):
    # Privileged users can see all requests; confirm the request exists.
    request_service.get_authorized(db, user, request_id)
    return comment_service.add_comment(
        db, request_id=request_id, author=user, body=body.body
    )
