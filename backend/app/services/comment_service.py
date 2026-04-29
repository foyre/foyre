"""Comment creation + listing. Kept tiny; history is recorded on each write."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.enums import HistoryEventType
from app.models.comment import RequestComment
from app.models.user import User
from app.repositories import comments as comments_repo
from app.services import history_service


def add_comment(db: Session, *, request_id: int, author: User, body: str) -> RequestComment:
    comment = comments_repo.create(
        db, RequestComment(request_id=request_id, author_id=author.id, body=body)
    )
    history_service.record_event(
        db,
        request_id=request_id,
        actor_id=author.id,
        event_type=HistoryEventType.commented,
        detail={"comment_id": comment.id},
    )
    return comment


def list_comments(db: Session, request_id: int) -> list[RequestComment]:
    return comments_repo.list_for_request(db, request_id)
