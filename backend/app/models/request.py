"""IntakeRequest: the core record a requester submits and reviewers review.

Structured form answers live in `payload` (JSON) so the form can evolve
without schema migrations; Pydantic enforces field-level validation.

Reviewer-assignment and provisioning-metadata columns are nullable and not
written by the current code paths. They exist to support future extensions
(assigned reviewer tracking, richer provisioning-state persistence) without
requiring a migration-heavy redesign.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.enums import RequestStatus

if TYPE_CHECKING:
    from app.models.comment import RequestComment
    from app.models.history import RequestHistoryEvent
    from app.models.user import User


class IntakeRequest(Base):
    __tablename__ = "intake_requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    status: Mapped[str] = mapped_column(
        String(32), default=RequestStatus.draft.value, index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Nullable extension points (not read by current code paths):
    assigned_reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    # Which provisioning backend a request is associated with
    # (e.g. "vcluster", "k3k", "namespace"). Populated by future orchestration.
    provisioning_target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Free-form per-provider blob (refs, state, errors). Stored as JSON to
    # accommodate multiple providers without a schema migration per field.
    provisioning_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    created_by: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by_id], back_populates="created_requests"
    )
    assigned_reviewer: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_reviewer_id], back_populates="assigned_requests"
    )
    comments: Mapped[list["RequestComment"]] = relationship(
        "RequestComment",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="RequestComment.id",
    )
    history_events: Mapped[list["RequestHistoryEvent"]] = relationship(
        "RequestHistoryEvent",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="RequestHistoryEvent.id",
    )
