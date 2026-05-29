"""Evidence produced by a validation run or step.

For MVP, all artifact bytes live in the database (per product decision:
"DB blobs"). If artifact sizes become a problem later, swap `content`
for a `storage_kind` + `storage_path` discriminator without touching
callers — readers should go through the repository's `read_bytes()`
helper rather than the column directly.

`step_result_id` is nullable so run-level artifacts (e.g., an aggregate
report produced after all steps) are representable.

Authorization mirrors the parent request: anyone who can see the
request can see its artifacts. Routes enforce this; the model itself
holds no access-control state.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.validation_run import ValidationRun
    from app.models.validation_step_result import ValidationStepResult


class ValidationArtifact(Base):
    __tablename__ = "validation_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    validation_run_id: Mapped[int] = mapped_column(
        ForeignKey("validation_runs.id"), index=True
    )
    step_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("validation_step_results.id"), nullable=True, index=True
    )

    # Display name shown in the UI (e.g., "workload-inventory.json").
    artifact_name: Mapped[str] = mapped_column(String(200))
    # Coarse category — matches the user's brief: json | yaml | text |
    # log | sarif | sbom | scan_result. Stored as string so adding
    # new types doesn't require a schema change.
    artifact_type: Mapped[str] = mapped_column(String(32))
    # MIME type for the download endpoint's Content-Type header.
    content_type: Mapped[str] = mapped_column(String(100), default="application/json")

    content: Mapped[bytes] = mapped_column(LargeBinary)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    validation_run: Mapped["ValidationRun"] = relationship(
        "ValidationRun", back_populates="artifacts"
    )
    step_result: Mapped["ValidationStepResult | None"] = relationship(
        "ValidationStepResult", back_populates="artifacts"
    )
