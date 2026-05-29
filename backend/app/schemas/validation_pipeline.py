"""DTOs for validation pipeline management.

The user-facing pipeline format is YAML, so create/update accept a
`definition_yaml` string rather than a structured body. The server
parses + validates it (see `validation_pipeline_service`). Responses
expose both the canonical YAML and the normalized JSON the runner uses.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PipelineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    definition_yaml: str = Field(min_length=1)
    enabled: bool = True
    is_default: bool = False


class PipelineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Absent = leave the definition unchanged (e.g. enable/disable only).
    definition_yaml: str | None = None
    enabled: bool | None = None


class PipelineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    display_name: str
    description: str | None
    enabled: bool
    is_default: bool
    version: int
    default_failure_policy: str
    definition_yaml: str
    definition_json: dict[str, Any]
    created_by_id: int | None
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime


class PipelineSummaryOut(BaseModel):
    """Lighter projection for list views (omits the full definition)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    display_name: str
    description: str | None
    enabled: bool
    is_default: bool
    version: int
    default_failure_policy: str
    created_at: datetime
    updated_at: datetime


class PipelineValidateRequest(BaseModel):
    """Validate a definition without persisting it (used by the editor)."""

    model_config = ConfigDict(extra="forbid")

    definition_yaml: str = Field(min_length=1)


class PipelineValidateResult(BaseModel):
    valid: bool
    # Present when valid: the normalized definition the runner would use.
    normalized: dict[str, Any] | None = None
    # Present when invalid: a human-readable validation error.
    error: str | None = None
