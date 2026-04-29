"""Validation environment endpoints (requester-facing)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.domain.enums import HistoryEventType, RequestStatus, Role, ValidationEnvStatus
from app.models.user import User
from app.provisioning import crypto
from app.provisioning.service import (
    ProvisioningUnavailable,
    start_provisioning,
    teardown,
)
from app.repositories import validation_environments as env_repo
from app.schemas.validation_environment import KubeconfigOut, ValidationEnvOut
from app.services import history_service, request_service

router = APIRouter()


def _get_request_or_403(
    db: Session, user: User, request_id: int
):
    """Owner or privileged users may act on the env; reuses existing authz."""
    return request_service.get_authorized(db, user, request_id)


@router.get(
    "/{request_id}/validation-environment", response_model=ValidationEnvOut | None
)
def get_current_env(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_request_or_403(db, user, request_id)
    return env_repo.current_for_request(db, request_id)


@router.post(
    "/{request_id}/validation-environment",
    response_model=ValidationEnvOut,
    status_code=202,
)
def create_env(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = _get_request_or_403(db, user, request_id)

    # The request owner is the primary actor here; admins can create on
    # behalf (useful when a requester needs help or provisioning previously
    # failed). Reviewer / architect cannot provision — they only review.
    is_admin = Role(user.role) == Role.admin
    if req.created_by_id != user.id and not is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "only the request owner or an admin can create a validation environment",
        )

    # Must be in submitted (or later) — no provisioning from draft.
    if RequestStatus(req.status) == RequestStatus.draft:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "submit the request before creating a validation environment",
        )

    # If there's already an active env, don't stack another one up.
    existing = env_repo.current_for_request(db, request_id)
    if existing and existing.status != ValidationEnvStatus.failed.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"this request already has a {existing.status} validation environment",
        )

    try:
        env = start_provisioning(db, request_id)
    except ProvisioningUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))

    history_service.record_event(
        db,
        request_id=request_id,
        actor_id=user.id,
        event_type=HistoryEventType.validation_env_requested,
        detail={"env_id": env.id, "vcluster_name": env.vcluster_name},
    )
    return env


@router.post(
    "/{request_id}/validation-environment/teardown",
    response_model=ValidationEnvOut,
)
def teardown_env(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_request_or_403(db, user, request_id)
    env = env_repo.current_for_request(db, request_id)
    if env is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no active validation environment")
    return teardown(db, env, actor_id=user.id)


@router.get(
    "/{request_id}/validation-environment/kubeconfig",
    response_model=KubeconfigOut,
)
def download_kubeconfig(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = _get_request_or_403(db, user, request_id)
    env = env_repo.current_for_request(db, request_id)
    if env is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no active validation environment")

    # Same ownership rule as create — only the requester can download.
    if req.created_by_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "only the request owner can download the kubeconfig",
        )
    if env.status != ValidationEnvStatus.ready.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"environment is {env.status}; kubeconfig available only when ready",
        )
    if env.user_kubeconfig_encrypted is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "kubeconfig missing from ready environment",
        )
    return KubeconfigOut(kubeconfig=crypto.decrypt(env.user_kubeconfig_encrypted))
