"""Reviewer comments / notes on an intake request."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.request import IntakeRequest
    from app.models.user import User


class RequestComment(Base):
    __tablename__ = "request_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("intake_requests.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    request: Mapped["IntakeRequest"] = relationship(
        "IntakeRequest", back_populates="comments"
    )
    author: Mapped["User"] = relationship("User", back_populates="authored_comments")
