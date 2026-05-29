"""Validation run executor.

Runs in a background thread (mirrors `app.provisioning.service`). Given a
queued `ValidationRun`, it:

  1. decrypts the validation environment's user kubeconfig;
  2. orders steps by their `dependsOn` graph (sequential execution for
     MVP — the data model supports parallel later);
  3. executes each enabled step under a per-step wall-clock timeout,
     passing prior step outcomes as `upstream`;
  4. persists a `ValidationStepResult` (+ any `ValidationArtifact`s) per
     step;
  5. aggregates step outcomes into the run's status + approval impact;
  6. records run start/finish history events on the request.

Threads can't be safely interrupted in Python, so a step that exceeds
its timeout is recorded as `error` while its worker thread is abandoned
(daemon). This is acceptable for MVP and documented for operators.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any

from app.db import SessionLocal
from app.domain.enums import (
    FailurePolicy,
    HistoryEventType,
    ValidationRunStatus,
    ValidationSeverity,
    ValidationStepStatus,
)
from app.models.validation_artifact import ValidationArtifact
from app.models.validation_step_result import ValidationStepResult
from app.provisioning import crypto
from app.repositories import validation_environments as env_repo
from app.repositories import validation_runs as runs_repo
from app.repositories import validation_step_results as steps_repo
from app.services import history_service
from app.validation import executors
from app.validation.types import (
    StepContext,
    StepOutcome,
    StepRollupInput,
    aggregate_run,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dependency ordering
# ---------------------------------------------------------------------------


def topo_order(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order steps so every step follows its dependencies.

    Stable: among steps with satisfied dependencies, original order is
    preserved. Assumes the definition has already been validated (no
    cycles / missing deps) by the pipeline parser; falls back to original
    order if something unexpected slips through.
    """
    by_name = {s["name"]: s for s in steps}
    remaining = list(steps)
    resolved: list[dict[str, Any]] = []
    resolved_names: set[str] = set()

    while remaining:
        progressed = False
        for s in list(remaining):
            deps = [d for d in (s.get("dependsOn") or []) if d in by_name]
            if all(d in resolved_names for d in deps):
                resolved.append(s)
                resolved_names.add(s["name"])
                remaining.remove(s)
                progressed = True
        if not progressed:
            # Shouldn't happen post-validation; append the rest as-is.
            resolved.extend(remaining)
            break
    return resolved


# ---------------------------------------------------------------------------
# Step execution
# ---------------------------------------------------------------------------


def _run_step_with_timeout(ctx: StepContext, timeout_seconds: int) -> StepOutcome:
    """Execute a step's executor under a wall-clock timeout.

    Disabled steps and unregistered step types are handled by the caller;
    this only runs when there's a real executor to invoke.
    """
    executor = executors.get_executor(ctx.step_type)
    if executor is None:
        return StepOutcome(
            status=ValidationStepStatus.skipped,
            summary=(
                f"Step type '{ctx.step_type}' is not executable in this "
                "version of Foyre; skipped."
            ),
        )

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(executor, ctx)
        return future.result(timeout=timeout_seconds)
    except FuturesTimeout:
        return StepOutcome(
            status=ValidationStepStatus.error,
            severity=ValidationSeverity.none,
            summary=f"Step timed out after {timeout_seconds}s.",
            error_message=f"timeout after {timeout_seconds}s",
        )
    except Exception as e:  # noqa: BLE001 - executor faults become step errors
        log.exception("step '%s' raised", ctx.step_name)
        return StepOutcome(
            status=ValidationStepStatus.error,
            severity=ValidationSeverity.none,
            summary="Step failed to execute.",
            error_message=f"{type(e).__name__}: {e}"[:2000],
        )
    finally:
        # Don't block on a possibly-hung worker thread.
        pool.shutdown(wait=False)


def _persist_step(
    db, run_id: int, step_def: dict[str, Any], sort_order: int, outcome: StepOutcome,
    started_at: datetime, completed_at: datetime,
) -> ValidationStepResult:
    row = ValidationStepResult(
        validation_run_id=run_id,
        step_name=step_def["name"],
        step_type=step_def["type"],
        display_name=step_def.get("displayName"),
        sort_order=sort_order,
        status=outcome.status.value,
        severity=outcome.severity.value,
        summary=outcome.summary or None,
        findings_json=outcome.findings or None,
        details_json=outcome.details or None,
        error_message=outcome.error_message,
        required=bool(step_def.get("required", False)),
        failure_policy=step_def.get("failurePolicy", FailurePolicy.warn.value),
        started_at=started_at,
        completed_at=completed_at,
    )
    row = steps_repo.save(db, row)
    for art in outcome.artifacts:
        db.add(
            ValidationArtifact(
                validation_run_id=run_id,
                step_result_id=row.id,
                artifact_name=art.name,
                artifact_type=art.artifact_type,
                content_type=art.content_type,
                content=art.content,
                size_bytes=len(art.content),
            )
        )
    db.commit()
    return row


# ---------------------------------------------------------------------------
# Run orchestration
# ---------------------------------------------------------------------------


def execute_run(run_id: int) -> None:
    """Worker entry point. Runs with its own DB session."""
    db = SessionLocal()
    try:
        run = runs_repo.get(db, run_id)
        if run is None:
            log.error("validation run %s disappeared before execution", run_id)
            return

        run.status = ValidationRunStatus.running.value
        runs_repo.save(db, run)

        try:
            kubeconfig_yaml = _resolve_kubeconfig(db, run)
        except Exception as e:  # noqa: BLE001
            _fail_run(db, run, f"could not access validation environment: {e}")
            return

        definition = run.pipeline_definition_json or {}
        steps = topo_order(list(definition.get("steps", [])))

        upstream: dict[str, StepOutcome] = {}
        type_map: dict[str, str] = {s["name"]: s["type"] for s in steps}
        rollup: list[StepRollupInput] = []
        artifact_total = 0

        for sort_order, step_def in enumerate(steps):
            started = datetime.now(tz=timezone.utc)
            if not step_def.get("enabled", True):
                outcome = StepOutcome(
                    status=ValidationStepStatus.skipped,
                    summary="Step disabled in pipeline definition.",
                )
            else:
                ctx = StepContext(
                    run_id=run.id,
                    step=step_def,
                    kubeconfig_yaml=kubeconfig_yaml,
                    upstream=dict(upstream),
                    upstream_type_map=dict(type_map),
                )
                outcome = _run_step_with_timeout(ctx, int(step_def.get("timeoutSeconds", 300)))
            completed = datetime.now(tz=timezone.utc)

            _persist_step(db, run.id, step_def, sort_order, outcome, started, completed)
            upstream[step_def["name"]] = outcome
            artifact_total += len(outcome.artifacts)
            rollup.append(
                StepRollupInput(
                    status=outcome.status,
                    failure_policy=FailurePolicy(
                        step_def.get("failurePolicy", FailurePolicy.warn.value)
                    ),
                )
            )

        run_status, impact = aggregate_run(rollup)
        _complete_run(db, run, run_status, impact, upstream, steps, artifact_total)
    except Exception as e:  # noqa: BLE001 - last-resort guard
        log.exception("validation run %s crashed", run_id)
        db2 = SessionLocal()
        try:
            run = runs_repo.get(db2, run_id)
            if run is not None:
                _fail_run(db2, run, f"{type(e).__name__}: {e}")
        finally:
            db2.close()
    finally:
        db.close()


def _resolve_kubeconfig(db, run) -> str:
    env = env_repo.get(db, run.validation_environment_id) if run.validation_environment_id else None
    if env is None or env.user_kubeconfig_encrypted is None:
        raise RuntimeError("validation environment has no kubeconfig")
    return crypto.decrypt(env.user_kubeconfig_encrypted)


def _summary_json(
    run_status: ValidationRunStatus,
    impact,
    upstream: dict[str, StepOutcome],
    steps: list[dict[str, Any]],
    artifact_total: int,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    finding_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    images: list[str] = []
    for step in steps:
        out = upstream.get(step["name"])
        if out is None:
            continue
        status_counts[out.status.value] = status_counts.get(out.status.value, 0) + 1
        for f in out.findings:
            sev = f.get("severity")
            if sev in finding_counts:
                finding_counts[sev] += 1
        if step["type"] == "builtin.workload_inventory":
            images = out.details.get("images", []) or images
    return {
        "status": run_status.value,
        "approvalImpact": impact.value,
        "stepCount": len(steps),
        "stepStatusCounts": status_counts,
        "findingCounts": finding_counts,
        "artifactCount": artifact_total,
        "images": images,
    }


def _complete_run(
    db, run, run_status: ValidationRunStatus, impact, upstream, steps, artifact_total: int
) -> None:
    run.status = run_status.value
    run.approval_impact = impact.value
    run.summary_json = _summary_json(run_status, impact, upstream, steps, artifact_total)
    run.completed_at = datetime.now(tz=timezone.utc)
    run.error_message = None
    runs_repo.save(db, run)
    history_service.record_event(
        db,
        request_id=run.request_id,
        actor_id=run.started_by_id or _owner_actor_id(db, run),
        event_type=HistoryEventType.validation_run_completed,
        detail={
            "run_id": run.id,
            "pipeline": run.pipeline_name,
            "status": run.status,
            "approval_impact": run.approval_impact,
        },
    )


def _fail_run(db, run, message: str) -> None:
    run.status = ValidationRunStatus.error.value
    run.error_message = message[:2000]
    run.completed_at = datetime.now(tz=timezone.utc)
    runs_repo.save(db, run)
    history_service.record_event(
        db,
        request_id=run.request_id,
        actor_id=run.started_by_id or _owner_actor_id(db, run),
        event_type=HistoryEventType.validation_run_failed,
        detail={"run_id": run.id, "error": run.error_message},
    )


def _owner_actor_id(db, run) -> int:
    from app.models.request import IntakeRequest

    req = db.get(IntakeRequest, run.request_id)
    return req.created_by_id if req else 1
