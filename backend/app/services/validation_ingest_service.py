"""Persist data pushed by a validation job's uploader sidecar.

Receives a normalized result + exit signals + artifact files for a
(run, step), enforces artifact limits, stores artifact bytes in
`validation_artifacts`, and parks the structured result in a
`validation_ingest_records` row for the runner to finalize against.

Limits (design §9) are enforced here because this is where untrusted job
output enters the system. Over-limit files are rejected and reported, not
silently stored, so an artifact flood can't bloat the DB.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import ValidationRunStatus
from app.models.validation_artifact import ValidationArtifact
from app.models.validation_ingest_record import ValidationIngestRecord
from app.repositories import validation_artifacts as artifacts_repo
from app.repositories import validation_ingest_records as ingest_repo
from app.repositories import validation_runs as runs_repo

# Limits. Conservative defaults; can be made chart-tunable later.
MAX_ARTIFACT_BYTES = 5 * 1024 * 1024          # 5 MiB per file
MAX_RUN_ARTIFACT_BYTES = 50 * 1024 * 1024     # 50 MiB total per run
MAX_ARTIFACTS_PER_RUN = 50                    # file count per run

_ALLOWED_TYPES = {"json", "yaml", "text", "log", "sarif", "sbom", "scan_result"}

# A run still accepting uploads must be actively executing.
_ACCEPTING_STATES = {ValidationRunStatus.queued.value, ValidationRunStatus.running.value}


@dataclass
class IngestSummary:
    stored: int = 0
    omitted: list[dict[str, str]] = field(default_factory=list)  # [{name, reason}]
    record_id: int | None = None


def _normalize_type(artifact_type: str | None) -> str:
    return artifact_type if artifact_type in _ALLOWED_TYPES else "text"


def ingest(
    db: Session,
    *,
    run_id: int,
    step_name: str,
    step_result_id: int | None,
    body: dict[str, Any],
) -> IngestSummary:
    """Validate + persist an ingest payload. Caller has already verified the
    token and that `run_id` matches the token's subject."""
    run = runs_repo.get(db, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "validation run not found")
    if run.status not in _ACCEPTING_STATES:
        # Late / replayed upload against a finished run.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"run is {run.status}; not accepting ingest uploads",
        )

    summary = IngestSummary()

    # Running totals for this run, so the per-run caps account for prior
    # steps' artifacts too.
    existing = artifacts_repo.list_for_run(db, run_id)
    run_bytes = sum(a.size_bytes for a in existing)
    run_count = len(existing)

    for art in body.get("artifacts") or []:
        name = str(art.get("name") or "artifact")
        b64 = art.get("content_b64")
        if not b64:
            summary.omitted.append({"name": name, "reason": "empty"})
            continue
        try:
            content = base64.b64decode(b64, validate=True)
        except (ValueError, TypeError):
            summary.omitted.append({"name": name, "reason": "invalid base64"})
            continue

        size = len(content)
        if size > MAX_ARTIFACT_BYTES:
            summary.omitted.append({"name": name, "reason": "file too large"})
            continue
        if run_count + 1 > MAX_ARTIFACTS_PER_RUN:
            summary.omitted.append({"name": name, "reason": "per-run file count exceeded"})
            continue
        if run_bytes + size > MAX_RUN_ARTIFACT_BYTES:
            summary.omitted.append({"name": name, "reason": "per-run size budget exceeded"})
            continue

        db.add(
            ValidationArtifact(
                validation_run_id=run_id,
                step_result_id=step_result_id,
                artifact_name=name,
                artifact_type=_normalize_type(art.get("artifact_type")),
                content_type=str(art.get("content_type") or "application/octet-stream"),
                content=content,
                size_bytes=size,
            )
        )
        run_bytes += size
        run_count += 1
        summary.stored += 1

    result_obj = body.get("result")
    if result_obj is not None and not isinstance(result_obj, dict):
        result_obj = None

    record = ValidationIngestRecord(
        validation_run_id=run_id,
        step_name=step_name,
        step_result_id=step_result_id,
        result_json=result_obj,
        exit_code=body.get("exit_code"),
        terminated_reason=body.get("terminated_reason"),
        job_state=body.get("job_state"),
        artifact_count=summary.stored,
        note="; ".join(f"{o['name']}: {o['reason']}" for o in summary.omitted) or None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    summary.record_id = record.id
    return summary
