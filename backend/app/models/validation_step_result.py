"""Result of one step inside a validation run.

`findings_json` is a list of `{severity, title, resource, message,
recommendation}` dicts (kept loose at the DB layer; shape enforced in
the service / step executors so adding new fields doesn't require a
migration).

`details_json` carries step-specific structured output that the UI can
render without re-parsing artifacts (e.g., image-scan summary counts by
severity, k8s-security counts by category, workload inventory rollup).
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.enums import (
    FailurePolicy,
    ValidationSeverity,
    ValidationStepStatus,
)

if TYPE_CHECKING:
    from app.models.validation_artifact import ValidationArtifact
    from app.models.validation_run import ValidationRun


class ValidationStepResult(Base):
    __tablename__ = "validation_step_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    validation_run_id: Mapped[int] = mapped_column(
        ForeignKey("validation_runs.id"), index=True
    )

    # Stable identifier within the run (matches `name` in the YAML spec).
    step_name: Mapped[str] = mapped_column(String(100))
    step_type: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(
        String(16), default=ValidationStepStatus.queued.value
    )
    severity: Mapped[str] = mapped_column(
        String(16), default=ValidationSeverity.none.value
    )

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Snapshot of the step's behavior fields so historical results are
    # interpretable even if the pipeline definition changed since.
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_policy: Mapped[str] = mapped_column(
        String(16), default=FailurePolicy.warn.value
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    validation_run: Mapped["ValidationRun"] = relationship(
        "ValidationRun", back_populates="step_results"
    )
    artifacts: Mapped[list["ValidationArtifact"]] = relationship(
        "ValidationArtifact",
        back_populates="step_result",
        order_by="ValidationArtifact.id",
    )
