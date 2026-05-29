"""Validation run orchestration.

Validates preconditions (a ready validation environment + configured
encryption), snapshots the chosen pipeline into a `ValidationRun`, records
a start event, and kicks off the runner in a background thread (mirrors
`app.provisioning.service`).

Routes call this module; they never touch the runner or repositories
directly.
"""
from __future__ import annotations

import threading

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import (
    HistoryEventType,
    ValidationEnvStatus,
    ValidationRunStatus,
)
from app.models.user import User
from app.models.validation_run import ValidationRun
from app.provisioning import crypto
from app.repositories import validation_environments as env_repo
from app.repositories import validation_runs as runs_repo
from app.services import history_service, validation_pipeline_service
from app.validation import runner

# Indirection so tests can run the pipeline synchronously instead of
# spawning a real thread.
_SPAWN = True


def _spawn_runner(run_id: int) -> None:
    if not _SPAWN:
        runner.execute_run(run_id)
        return
    t = threading.Thread(
        target=runner.execute_run,
        args=(run_id,),
        name=f"validation-run-{run_id}",
        daemon=True,
    )
    t.start()


def start_run(
    db: Session,
    user: User,
    request_id: int,
    *,
    pipeline_id: int | None,
    reason: str | None,
) -> ValidationRun:
    """Create + launch a validation run for a request's current env.

    Caller is responsible for authorization (the route checks the user can
    act on this request and holds a privileged role).
    """
    env = env_repo.current_for_request(db, request_id)
    if env is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "this request has no validation environment to validate against",
        )
    if env.status != ValidationEnvStatus.ready.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"validation environment is {env.status}; it must be ready before running a pipeline",
        )
    if env.user_kubeconfig_encrypted is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "validation environment is missing its kubeconfig",
        )
    if not crypto.is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "APP_SECRET_KEY is not configured; cannot decrypt the environment kubeconfig",
        )

    pipeline = validation_pipeline_service.resolve_for_run(db, pipeline_id)

    run = ValidationRun(
        request_id=request_id,
        validation_environment_id=env.id,
        pipeline_id=pipeline.id,
        pipeline_name=pipeline.name,
        pipeline_version=pipeline.version,
        pipeline_definition_json=pipeline.definition_json,
        status=ValidationRunStatus.queued.value,
        started_by_id=user.id,
        reason=reason,
    )
    run = runs_repo.save(db, run)

    history_service.record_event(
        db,
        request_id=request_id,
        actor_id=user.id,
        event_type=HistoryEventType.validation_run_started,
        detail={
            "run_id": run.id,
            "pipeline": pipeline.name,
            "pipeline_version": pipeline.version,
        },
    )

    _spawn_runner(run.id)
    return run


def list_runs(db: Session, request_id: int) -> list[ValidationRun]:
    return runs_repo.list_for_request(db, request_id)


def get_run(db: Session, run_id: int) -> ValidationRun:
    run = runs_repo.get(db, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "validation run not found")
    return run
