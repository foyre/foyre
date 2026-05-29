"""Single-row admin-tunable policy controlling how validation results
gate the approval transition.

Mirrors the `form_schema_configs` pattern: at most one row, identified
by a fixed primary key. If no row exists, callers fall back to the
defaults declared on this model.

Defaults (matching the brief):
  - require_validation_before_approval: False
      → approving a request without a completed run is allowed.
  - block_approval_on_failed_validation: True
      → approval fails if the latest run had any blocking step failures.
  - allow_validation_override: True
      → admins / privileged roles can override a blocked approval by
        passing `override_validation` + `override_reason` on the
        status-change request. Override is recorded in request history.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class ValidationPolicyConfig(Base):
    __tablename__ = "validation_policy_configs"

    id: Mapped[int] = mapped_column(primary_key=True)

    require_validation_before_approval: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    block_approval_on_failed_validation: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1"
    )
    allow_validation_override: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1"
    )

    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped["User | None"] = relationship("User")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
