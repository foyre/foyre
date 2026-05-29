"""Validation pipeline management endpoints.

Paths follow the feature brief: `/api/validation/pipelines`. Mutations
are admin-only (only admins author pipelines); reads are open to
privileged roles so reviewers can list pipelines to pick one for a run
(chunk 3).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_role
from app.domain.enums import Role
from app.models.user import User
from app.schemas.validation_pipeline import (
    PipelineCreate,
    PipelineOut,
    PipelineSummaryOut,
    PipelineUpdate,
    PipelineValidateRequest,
    PipelineValidateResult,
)
from app.services import validation_pipeline_service as svc

router = APIRouter()

# Reviewers/architects/admins can read pipelines (needed to choose one to
# run); only admins can mutate them.
_read_guard = require_role(Role.reviewer, Role.architect, Role.admin)
_admin_guard = require_role(Role.admin)


@router.get("", response_model=list[PipelineSummaryOut])
def list_pipelines(
    db: Session = Depends(get_db),
    _: User = Depends(_read_guard),
):
    return svc.list_pipelines(db)


@router.post("", response_model=PipelineOut, status_code=201)
def create_pipeline(
    body: PipelineCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_admin_guard),
):
    return svc.create_pipeline(
        db,
        user,
        definition_yaml=body.definition_yaml,
        enabled=body.enabled,
        is_default=body.is_default,
    )


@router.post("/validate", response_model=PipelineValidateResult)
def validate_pipeline(
    body: PipelineValidateRequest,
    _: User = Depends(_admin_guard),
):
    """Validate a definition without persisting it. Always returns 200;
    the `valid` flag + `error` carry the outcome so the editor can show
    inline feedback rather than handling a 4xx."""
    try:
        normalized = svc.parse_and_validate(body.definition_yaml)
    except HTTPException as e:
        return PipelineValidateResult(valid=False, error=str(e.detail))
    return PipelineValidateResult(valid=True, normalized=normalized)


@router.get("/{pipeline_id}", response_model=PipelineOut)
def get_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_read_guard),
):
    return svc.get_pipeline(db, pipeline_id)


@router.put("/{pipeline_id}", response_model=PipelineOut)
def update_pipeline(
    pipeline_id: int,
    body: PipelineUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_admin_guard),
):
    return svc.update_pipeline(
        db,
        user,
        pipeline_id,
        definition_yaml=body.definition_yaml,
        enabled=body.enabled,
    )


@router.delete("/{pipeline_id}", status_code=204)
def delete_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_admin_guard),
):
    svc.delete_pipeline(db, pipeline_id)


@router.post("/{pipeline_id}/set-default", response_model=PipelineOut)
def set_default_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_admin_guard),
):
    return svc.set_default(db, pipeline_id)
