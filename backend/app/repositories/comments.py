from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.comment import RequestComment


def list_for_request(db: Session, request_id: int) -> list[RequestComment]:
    stmt = (
        select(RequestComment)
        .options(selectinload(RequestComment.author))
        .where(RequestComment.request_id == request_id)
        .order_by(RequestComment.id.asc())
    )
    return list(db.execute(stmt).scalars())


def create(db: Session, comment: RequestComment) -> RequestComment:
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
