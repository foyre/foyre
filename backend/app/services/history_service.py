"""Append-only history writer. Every mutating service calls `record_event`."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.enums import HistoryEventType
from app.models.history import RequestHistoryEvent
from app.repositories import history as history_repo


def record_event(
    db: Session,
    *,
    request_id: int,
    actor_id: int,
    event_type: HistoryEventType,
    detail: dict | None = None,
) -> RequestHistoryEvent:
    event = RequestHistoryEvent(
        request_id=request_id,
        actor_id=actor_id,
        event_type=event_type.value,
        detail=detail,
    )
    return history_repo.create(db, event)
