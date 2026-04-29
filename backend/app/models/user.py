"""User identity model.

Local identity today. When external providers (LDAP/AD/OIDC) are added, this
row stays the canonical local record; a provider maps external identities onto
it (creating one on first successful auth if desired).
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.enums import Role

if TYPE_CHECKING:
    from app.models.comment import RequestComment
    from app.models.history import RequestHistoryEvent
    from app.models.request import IntakeRequest


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=Role.requester.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # True when the user must change their password before proceeding.
    # Set on admin-created users so they rotate the temp password on first login.
    # Cleared by a successful /users/me/password call.
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    created_requests: Mapped[list["IntakeRequest"]] = relationship(
        "IntakeRequest",
        foreign_keys="IntakeRequest.created_by_id",
        back_populates="created_by",
    )
    assigned_requests: Mapped[list["IntakeRequest"]] = relationship(
        "IntakeRequest",
        foreign_keys="IntakeRequest.assigned_reviewer_id",
        back_populates="assigned_reviewer",
    )
    authored_comments: Mapped[list["RequestComment"]] = relationship(
        "RequestComment", back_populates="author"
    )
    authored_events: Mapped[list["RequestHistoryEvent"]] = relationship(
        "RequestHistoryEvent", back_populates="actor"
    )
