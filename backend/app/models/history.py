"""Append-only history of events per request.

Written exclusively via `history_service.record_event`. Kept lightweight; this
is not a full enterprise audit log.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.request import IntakeRequest
    from app.models.user import User


class RequestHistoryEvent(Base):
    __tablename__ = "request_history_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("intake_requests.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    request: Mapped["IntakeRequest"] = relationship(
        "IntakeRequest", back_populates="history_events"
    )
    actor: Mapped["User"] = relationship("User", back_populates="authored_events")
