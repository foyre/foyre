"""One execution of a validation pipeline against a request's env.

A run snapshots the exact pipeline definition at start time
(`pipeline_definition_json` + `pipeline_version`) so that:

  - Editing or deleting the source pipeline never changes historical run
    results.
  - The UI can render the run using the snapshot regardless of the
    pipeline's current state.

`approval_impact` is derived from the step results' failure policies and
materialized here so the approval gate doesn't have to recompute on
every status-change request.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.enums import ApprovalImpact, ValidationRunStatus

if TYPE_CHECKING:
    from app.models.request import IntakeRequest
    from app.models.user import User
    from app.models.validation_artifact import ValidationArtifact
    from app.models.validation_environment import ValidationEnvironment
    from app.models.validation_pipeline import ValidationPipeline
    from app.models.validation_step_result import ValidationStepResult


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)

    request_id: Mapped[int] = mapped_column(
        ForeignKey("intake_requests.id"), index=True
    )
    # Nullable: the env may be torn down after the run completes; we want
    # historical runs to survive that.
    validation_environment_id: Mapped[int | None] = mapped_column(
        ForeignKey("validation_environments.id"), nullable=True, index=True
    )
    # Nullable: the pipeline row may be deleted; the snapshot below is
    # what authoritatively defines what ran.
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("validation_pipelines.id"), nullable=True, index=True
    )

    # Snapshot of the pipeline at run-start time.
    pipeline_name: Mapped[str] = mapped_column(String(100))
    pipeline_version: Mapped[int] = mapped_column(Integer)
    pipeline_definition_json: Mapped[dict] = mapped_column(JSON)

    status: Mapped[str] = mapped_column(
        String(16), default=ValidationRunStatus.queued.value, index=True
    )
    approval_impact: Mapped[str] = mapped_column(
        String(16), default=ApprovalImpact.none.value
    )

    started_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    # Optional reviewer note explaining why this run was started.
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Aggregated counts + summary the UI can render without joining
    # ValidationStepResult on every request.
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships ----------------------------------------------------------
    request: Mapped["IntakeRequest"] = relationship("IntakeRequest")
    validation_environment: Mapped["ValidationEnvironment | None"] = relationship(
        "ValidationEnvironment"
    )
    pipeline: Mapped["ValidationPipeline | None"] = relationship("ValidationPipeline")
    started_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[started_by_id]
    )

    # Cascade delete owned step results + artifacts when a run is purged.
    step_results: Mapped[list["ValidationStepResult"]] = relationship(
        "ValidationStepResult",
        back_populates="validation_run",
        cascade="all, delete-orphan",
        order_by="ValidationStepResult.sort_order",
    )
    artifacts: Mapped[list["ValidationArtifact"]] = relationship(
        "ValidationArtifact",
        back_populates="validation_run",
        cascade="all, delete-orphan",
        order_by="ValidationArtifact.id",
    )
