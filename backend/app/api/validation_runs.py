"""Validation run + artifact endpoints.

Paths follow the feature brief:
  - POST /api/requests/{request_id}/validation-runs   (trigger)
  - GET  /api/requests/{request_id}/validation-runs   (list)
  - GET  /api/validation-runs/{run_id}                (detail)
  - GET  /api/validation-runs/{run_id}/artifacts      (artifact metadata)
  - GET  /api/validation-artifacts/{artifact_id}/download

Authorization reuses the request's existing rules: anyone who can see the
request can see its runs + artifacts; only privileged roles
(reviewer/architect/admin) can *trigger* a run.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.domain.enums import PRIVILEGED_ROLES, Role
from app.models.user import User
from app.repositories import validation_artifacts as artifacts_repo
from app.schemas.validation_policy import ApprovalGateOut
from app.schemas.validation_run import (
    ArtifactOut,
    RunCreate,
    RunOut,
    RunSummaryOut,
)
from app.services import (
    request_service,
    validation_approval_service,
    validation_run_service,
)

router = APIRouter()


@router.post(
    "/requests/{request_id}/validation-runs",
    response_model=RunOut,
    status_code=202,
)
def start_validation_run(
    request_id: int,
    body: RunCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Visibility check (owner or privileged); 404/403 as appropriate.
    request_service.get_authorized(db, user, request_id)
    # Only reviewers/architects/admins may trigger a run.
    if Role(user.role) not in PRIVILEGED_ROLES:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "only reviewers, architects, or admins can run validation pipelines",
        )
    return validation_run_service.start_run(
        db, user, request_id, pipeline_id=body.pipeline_id, reason=body.reason
    )


@router.get(
    "/requests/{request_id}/validation-runs",
    response_model=list[RunSummaryOut],
)
def list_validation_runs(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request_service.get_authorized(db, user, request_id)
    return validation_run_service.list_runs(db, request_id)


@router.get(
    "/requests/{request_id}/validation-approval",
    response_model=ApprovalGateOut,
)
def get_approval_gate(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Whether the latest validation state permits approving this request.

    Read-only; the UI uses it to render the approve button + warnings.
    """
    request_service.get_authorized(db, user, request_id)
    gate = validation_approval_service.evaluate(db, request_id)
    return ApprovalGateOut(
        blocked=gate.blocked,
        impact=gate.impact.value,
        reason=gate.reason,
        override_allowed=gate.override_allowed,
        missing_validation=gate.missing_validation,
        latest_run_id=gate.latest_run.id if gate.latest_run else None,
    )


@router.get("/validation-runs/{run_id}", response_model=RunOut)
def get_validation_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = validation_run_service.get_run(db, run_id)
    request_service.get_authorized(db, user, run.request_id)
    return run


@router.get(
    "/validation-runs/{run_id}/artifacts",
    response_model=list[ArtifactOut],
)
def list_run_artifacts(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = validation_run_service.get_run(db, run_id)
    request_service.get_authorized(db, user, run.request_id)
    return artifacts_repo.list_for_run(db, run_id)


@router.get("/validation-artifacts/{artifact_id}/download")
def download_artifact(
    artifact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    artifact = artifacts_repo.get(db, artifact_id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "artifact not found")
    # Authorize against the parent run's request.
    run = validation_run_service.get_run(db, artifact.validation_run_id)
    request_service.get_authorized(db, user, run.request_id)

    content = artifacts_repo.read_bytes(artifact)
    return Response(
        content=content,
        media_type=artifact.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.artifact_name}"'
        },
    )
