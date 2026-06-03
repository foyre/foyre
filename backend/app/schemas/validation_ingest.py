"""DTOs for the validation ingest endpoint (sidecar → Foyre)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IngestArtifactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    artifact_type: str | None = None
    content_type: str | None = None
    # Base64-encoded file bytes.
    content_b64: str


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Main-container outcome signals (the sidecar reports these).
    exit_code: int | None = None
    terminated_reason: str | None = None
    job_state: str | None = None
    # Optional normalized result object (the contents of result.json).
    result: dict[str, Any] | None = None
    artifacts: list[IngestArtifactIn] = []


class IngestResult(BaseModel):
    stored: int
    omitted: list[dict[str, str]]
    record_id: int | None
