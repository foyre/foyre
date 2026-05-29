"""DTOs for validation runs, step results, and artifacts.

Artifact responses never include the raw `content` — that's served only
by the dedicated download endpoint, with the same authorization as the
parent request.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Omit to use the configured default pipeline.
    pipeline_id: int | None = None
    reason: str | None = Field(default=None, max_length=2000)


class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    validation_run_id: int
    step_result_id: int | None
    artifact_name: str
    artifact_type: str
    content_type: str
    size_bytes: int
    created_at: datetime


class StepResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_name: str
    step_type: str
    display_name: str | None
    sort_order: int
    status: str
    severity: str
    summary: str | None
    findings_json: list[Any] | None
    details_json: dict[str, Any] | None
    error_message: str | None
    required: bool
    failure_policy: str
    started_at: datetime | None
    completed_at: datetime | None
    artifacts: list[ArtifactOut] = []


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    validation_environment_id: int | None
    pipeline_id: int | None
    pipeline_name: str
    pipeline_version: int
    status: str
    approval_impact: str
    started_by_id: int | None
    reason: str | None
    summary_json: dict[str, Any] | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    step_results: list[StepResultOut] = []


class RunSummaryOut(BaseModel):
    """Lighter projection for list views (no step results)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    pipeline_id: int | None
    pipeline_name: str
    pipeline_version: int
    status: str
    approval_impact: str
    started_by_id: int | None
    summary_json: dict[str, Any] | None
    started_at: datetime
    completed_at: datetime | None
