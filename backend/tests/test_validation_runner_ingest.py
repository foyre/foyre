"""Runner wiring for the push-model ingest path (Chunk 4b).

Exercises execute_run synchronously with a fake custom.kubernetes_job
executor that simulates the uploader sidecar (writes an ingest record +
artifact on a separate session). Verifies: the step row is pre-created and
finalized once, result.json overrides the provisional outcome, sidecar +
executor artifacts both attach, and the config gate toggles log-only mode.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.domain.enums import ValidationEnvStatus, ValidationRunStatus, ValidationStepStatus
from app.models.request import IntakeRequest
from app.models.user import User
from app.models.validation_artifact import ValidationArtifact
from app.models.validation_environment import ValidationEnvironment
from app.models.validation_ingest_record import ValidationIngestRecord
from app.models.validation_run import ValidationRun
from app.provisioning import crypto
from app.repositories import (
    validation_artifacts as artifacts_repo,
    validation_step_results as steps_repo,
)
from app.services import validation_pipeline_service  # noqa: F401 (model registration)
from app.validation import executors, runner
from app.validation.types import ArtifactDraft, StepContext, StepOutcome


CUSTOM_STEP_DEF = {
    "name": "company-check",
    "type": "custom.kubernetes_job",
    "displayName": "Company Check",
    "enabled": True,
    "required": False,
    "dependsOn": [],
    "timeoutSeconds": 60,
    "failurePolicy": "warn",
    "config": {"image": "registry.example.com/checker:latest"},
}


@pytest.fixture
def SessionLocal(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SL = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr(runner, "SessionLocal", SL)
    monkeypatch.setattr(crypto, "decrypt", lambda b: "fake-kubeconfig")
    return SL


def _make_run(SL) -> int:
    s = SL()
    u = User(username="o", email="o@e.com", password_hash="x", role="requester", is_active=True)
    s.add(u)
    s.commit()
    s.refresh(u)
    req = IntakeRequest(created_by_id=u.id, status="under_review", payload={})
    s.add(req)
    s.commit()
    s.refresh(req)
    env = ValidationEnvironment(
        request_id=req.id,
        host_cluster_config_id=1,
        status=ValidationEnvStatus.ready.value,
        namespace="ns",
        vcluster_name="vc",
        provider="vcluster",
        user_kubeconfig_encrypted=b"enc",
    )
    s.add(env)
    s.commit()
    s.refresh(env)
    run = ValidationRun(
        request_id=req.id,
        validation_environment_id=env.id,
        pipeline_name="p",
        pipeline_version=1,
        pipeline_definition_json={"steps": [CUSTOM_STEP_DEF]},
        status=ValidationRunStatus.queued.value,
    )
    s.add(run)
    s.commit()
    rid = run.id
    s.close()
    return rid


def _fake_executor(SL, sidecar_result, captured):
    def fake(ctx: StepContext) -> StepOutcome:
        captured["ingest_token"] = ctx.ingest_token
        captured["step_result_id"] = ctx.step_result_id
        captured["runner_image"] = ctx.runner_image
        # Simulate the uploader sidecar (separate session + commit).
        if ctx.ingest_token and sidecar_result is not None:
            s = SL()
            try:
                s.add(
                    ValidationIngestRecord(
                        validation_run_id=ctx.run_id,
                        step_name=ctx.step_name,
                        step_result_id=ctx.step_result_id,
                        result_json=sidecar_result,
                    )
                )
                s.add(
                    ValidationArtifact(
                        validation_run_id=ctx.run_id,
                        step_result_id=ctx.step_result_id,
                        artifact_name="result.json",
                        artifact_type="json",
                        content_type="application/json",
                        content=b"{}",
                        size_bytes=2,
                    )
                )
                s.commit()
            finally:
                s.close()
        # Provisional outcome (exit-code path) + the executor's log artifact.
        return StepOutcome(
            status=ValidationStepStatus.passed,
            summary="exit 0",
            artifacts=[
                ArtifactDraft(
                    name="job-logs.txt",
                    artifact_type="log",
                    content=b"logs",
                    content_type="text/plain",
                )
            ],
        )

    return fake


def test_push_mode_result_json_overrides_and_artifacts_merge(SessionLocal, monkeypatch):
    monkeypatch.setattr(runner.settings, "validation_ingest_base_url", "http://foyre:8000")
    monkeypatch.setattr(runner.settings, "validation_runner_image", "foyre-runner:test")
    captured: dict = {}
    sidecar_result = {
        "status": "failed",
        "severity": "high",
        "summary": "blocked by policy",
        "findings": [{"severity": "high", "title": "bad"}],
    }
    monkeypatch.setitem(
        executors._REGISTRY,
        "custom.kubernetes_job",
        _fake_executor(SessionLocal, sidecar_result, captured),
    )

    rid = _make_run(SessionLocal)
    runner.execute_run(rid)

    # The runner wired the sidecar.
    assert captured["ingest_token"] is not None
    assert captured["step_result_id"] is not None
    assert captured["runner_image"] == "foyre-runner:test"

    db = SessionLocal()
    try:
        steps = steps_repo.list_for_run(db, rid)
        assert len(steps) == 1  # pre-created + finalized, not duplicated
        step = steps[0]
        # result.json (ingest) overrode the provisional exit-0 outcome.
        assert step.status == ValidationStepStatus.failed.value
        assert step.severity == "high"
        assert step.summary == "blocked by policy"
        assert step.details_json.get("resultSource") == "result.json (ingest)"
        # Both the sidecar artifact and the executor's log are attached.
        names = {a.artifact_name for a in artifacts_repo.list_for_run(db, rid)}
        assert names == {"result.json", "job-logs.txt"}
    finally:
        db.close()


def test_log_only_mode_when_push_not_configured(SessionLocal, monkeypatch):
    # Push disabled (no base URL / runner image) → log-only, no token.
    monkeypatch.setattr(runner.settings, "validation_ingest_base_url", "")
    monkeypatch.setattr(runner.settings, "validation_runner_image", "")
    captured: dict = {}
    monkeypatch.setitem(
        executors._REGISTRY,
        "custom.kubernetes_job",
        _fake_executor(SessionLocal, sidecar_result=None, captured=captured),
    )

    rid = _make_run(SessionLocal)
    runner.execute_run(rid)

    assert captured["ingest_token"] is None  # no sidecar wiring
    assert captured["step_result_id"] is not None  # row still pre-created

    db = SessionLocal()
    try:
        steps = steps_repo.list_for_run(db, rid)
        assert len(steps) == 1
        # Provisional outcome stands (no ingest override).
        assert steps[0].status == ValidationStepStatus.passed.value
        names = {a.artifact_name for a in artifacts_repo.list_for_run(db, rid)}
        assert names == {"job-logs.txt"}
    finally:
        db.close()
