from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import HistoryEventType
from app.schemas.user import UserRef


class HistoryEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    actor_id: int
    actor: UserRef | None = None
    event_type: HistoryEventType
    detail: dict | None
    created_at: datetime
