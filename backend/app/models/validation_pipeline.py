"""Reusable validation pipeline definition.

A pipeline is a named, versioned, declarative description of validation
steps to run against an AI workload deployed in a Foyre validation
environment. Pipelines are authored as YAML by admins; we keep both the
canonical YAML (so `View YAML` round-trips byte-for-byte and preserves
comments) and the parsed JSON (used by the runner so it doesn't re-parse
on every run).

Versioning: `version` increments on each PUT. A `ValidationRun` snapshots
the exact pipeline definition at run start so historical results stay
meaningful even if the pipeline is later edited or deleted.

Default-pipeline uniqueness is enforced at the service layer (mirrors
`HostClusterConfig.is_default` rather than a partial unique index, which
SQLite supports inconsistently across versions).
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class ValidationPipeline(Base):
    __tablename__ = "validation_pipelines"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Machine name; matches the `metadata.name` field in the pipeline YAML
    # and is used as the natural key when seeding/upserting defaults.
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Bumped on every PUT. ValidationRun.pipeline_version stores the value
    # at run-start time.
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Default failure policy applied to steps that don't specify one.
    # Stored as a string so future enum additions don't require a migration.
    default_failure_policy: Mapped[str] = mapped_column(String(16), default="warn")

    # Canonical YAML as authored by the admin (preserves comments + ordering).
    definition_yaml: Mapped[str] = mapped_column(Text)
    # Parsed + normalized definition the runner consumes directly.
    definition_json: Mapped[dict] = mapped_column(JSON)

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # One-way relationships (no back_populates) keep User small.
    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by_id]
    )
    updated_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[updated_by_id]
    )
