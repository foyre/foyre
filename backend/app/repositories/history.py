from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.history import RequestHistoryEvent


def list_for_request(db: Session, request_id: int) -> list[RequestHistoryEvent]:
    stmt = (
        select(RequestHistoryEvent)
        .options(selectinload(RequestHistoryEvent.actor))
        .where(RequestHistoryEvent.request_id == request_id)
        .order_by(RequestHistoryEvent.id.asc())
    )
    return list(db.execute(stmt).scalars())


def create(db: Session, event: RequestHistoryEvent) -> RequestHistoryEvent:
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
