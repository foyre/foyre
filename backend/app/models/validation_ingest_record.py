"""Staging record for data pushed by a validation job's uploader sidecar.

The runner pre-creates a step result, launches the job, and the job's
sidecar POSTs its result (`result.json`) + exit metadata to the ingest
endpoint. That arrives *before* the runner finalizes the step, so it's
parked here keyed by (run, step) for the runner to pick up when the job
completes. Uploaded artifact *bytes* go straight into `validation_artifacts`;
this row holds the small structured result + exit signals.

A dedicated table (rather than new columns on `validation_step_results`)
keeps the change additive — the no-migrations model auto-creates new
tables but does not alter existing ones.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ValidationIngestRecord(Base):
    __tablename__ = "validation_ingest_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    validation_run_id: Mapped[int] = mapped_column(
        ForeignKey("validation_runs.id"), index=True
    )
    step_name: Mapped[str] = mapped_column(String(100), index=True)
    step_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("validation_step_results.id"), nullable=True
    )

    # The normalized result object the job emitted (result.json), if any.
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Main-container exit signals reported by the sidecar.
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    terminated_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # How many artifact files this upload stored (for diagnostics).
    artifact_count: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
