"""Stored admin customization of the intake form schema.

Foyre ships with a built-in default schema (see app.domain.form_schema). Admins
can customize section ordering, section titles, field labels, and add custom
fields via the admin UI. Their customization is persisted as a single row in
this table (row id = 1). If no row exists, the default schema is served.

Why a single-row table rather than a JSON file on disk?
  - Works for both SQLite and Postgres deployments.
  - Survives container restarts in a way config files don't.
  - Carries `updated_by_id` + timestamp for auditability.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class FormSchemaConfig(Base):
    __tablename__ = "form_schema_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Full schema document: {"sections": [...]}. Validated server-side before
    # being written here; see app.services.form_schema_service.
    sections: Mapped[list] = mapped_column(JSON, default=list)

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
