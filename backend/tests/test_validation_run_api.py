"""End-to-end validation run tests (Chunk 3).

The pipeline runner is forced to execute synchronously and the real
cluster-touching executors are replaced with fakes via the executor
registry, so these tests exercise the full create → execute → persist →
fetch → download path without a Kubernetes cluster.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.passwords import hash_password
from app.auth.tokens import issue_token
from app.db import Base, get_db
from app.domain.default_pipeline import DEFAULT_PIPELINE_YAML
from app.domain.enums import Role, ValidationEnvStatus
from app.main import create_app
from app.models.request import IntakeRequest
from app.models.user import User
from app.models.validation_environment import ValidationEnvironment
from app.provisioning import crypto
from app.services import validation_pipeline_service, validation_run_service
from app.validation import executors
from app.validation.types import ArtifactDraft, StepContext, StepOutcome
from app.domain.enums import ValidationSeverity, ValidationStepStatus


@pytest.fixture
def app_and_session(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    # The runner uses its own SessionLocal(); point it at the test engine.
    monkeypatch.setattr("app.validation.runner.SessionLocal", SessionLocal)
    # Execute synchronously so assertions run after the pipeline finishes.
    monkeypatch.setattr(validation_run_service, "_SPAWN", False)
    # Encryption: stub crypto so we don't need a real Fernet key.
    monkeypatch.setattr(crypto, "is_configured", lambda: True)
    monkeypatch.setattr(crypto, "decrypt", lambda b: "fake-kubeconfig-yaml")

    app = create_app()

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return app, SessionLocal


def _user(SessionLocal, role: Role, username: str) -> tuple[int, str]:
    db = SessionLocal()
    u = User(
        username=username,
        email=f"{username}@e.com",
        password_hash=hash_password("x"),
        role=role.value,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    tok = issue_token(subject=str(u.id), extra={"role": u.role})
    uid = u.id
    db.close()
    return uid, tok


def _request_with_ready_env(SessionLocal, owner_id: int) -> int:
    db = SessionLocal()
    req = IntakeRequest(created_by_id=owner_id, status="submitted", payload={})
    db.add(req)
    db.commit()
    db.refresh(req)
    env = ValidationEnvironment(
        request_id=req.id,
        host_cluster_config_id=1,
        status=ValidationEnvStatus.ready.value,
        namespace="ns",
        vcluster_name="vc",
        provider="vcluster",
        user_kubeconfig_encrypted=b"encrypted-bytes",
    )
    db.add(env)
    db.commit()
    rid = req.id
    db.close()
    return rid


def _seed_default_pipeline(SessionLocal, admin_id: int):
    db = SessionLocal()
    admin = db.get(User, admin_id)
    validation_pipeline_service.create_pipeline(
        db, admin, definition_yaml=DEFAULT_PIPELINE_YAML, is_default=True
    )
    db.close()


def _auth(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


# A fake executor that records a finding + an artifact, used to replace the
# real cluster-touching executors.
def _fake_executor(ctx: StepContext) -> StepOutcome:
    return StepOutcome(
        status=ValidationStepStatus.passed,
        severity=ValidationSeverity.none,
        summary=f"fake {ctx.step_name} ok",
        findings=[],
        details={"images": ["ghcr.io/example/app:latest"]},
        artifacts=[
            ArtifactDraft(
                name=f"{ctx.step_name}.json",
                artifact_type="json",
                content=b'{"ok": true}',
                content_type="application/json",
            )
        ],
    )


@pytest.fixture(autouse=True)
def _register_fake_executors(monkeypatch):
    """Replace real executors with fakes for the duration of each test."""
    monkeypatch.setitem(executors._REGISTRY, "builtin.workload_inventory", _fake_executor)
    monkeypatch.setitem(executors._REGISTRY, "builtin.kubernetes_security", _fake_executor)
    # image_scan stays unregistered → runner records it as skipped.


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_reviewer_runs_default_pipeline_end_to_end(app_and_session):
    app, SessionLocal = app_and_session
    admin_id, _ = _user(SessionLocal, Role.admin, "admin")
    _seed_default_pipeline(SessionLocal, admin_id)
    owner_id, _ = _user(SessionLocal, Role.requester, "owner")
    reviewer_id, rev_tok = _user(SessionLocal, Role.reviewer, "rev")
    rid = _request_with_ready_env(SessionLocal, owner_id)

    client = TestClient(app)
    r = client.post(
        f"/api/requests/{rid}/validation-runs",
        json={"reason": "pre-prod check"},
        headers=_auth(rev_tok),
    )
    assert r.status_code == 202, r.text
    run = r.json()
    run_id = run["id"]

    # Ran synchronously → fetch detail and assert step results persisted.
    detail = client.get(f"/api/validation-runs/{run_id}", headers=_auth(rev_tok)).json()
    assert detail["status"] in ("passed", "warning", "failed")
    step_names = [s["step_name"] for s in detail["step_results"]]
    assert step_names == ["workload-inventory", "kubernetes-security", "image-scan"]
    by_name = {s["step_name"]: s for s in detail["step_results"]}
    assert by_name["workload-inventory"]["status"] == "passed"
    # image-scan has no registered executor in chunk 3 → skipped.
    assert by_name["image-scan"]["status"] == "skipped"
    # Default pipeline: inventory warns, security+image-scan block. With fakes
    # passing and image-scan skipped, run should be passed.
    assert detail["status"] == "passed"
    assert detail["approval_impact"] == "none"
    assert detail["summary_json"]["images"] == ["ghcr.io/example/app:latest"]


def test_requester_cannot_trigger_but_can_view(app_and_session):
    app, SessionLocal = app_and_session
    admin_id, _ = _user(SessionLocal, Role.admin, "admin")
    _seed_default_pipeline(SessionLocal, admin_id)
    owner_id, owner_tok = _user(SessionLocal, Role.requester, "owner")
    rid = _request_with_ready_env(SessionLocal, owner_id)

    client = TestClient(app)
    # Owner (requester) cannot trigger.
    r = client.post(f"/api/requests/{rid}/validation-runs", json={}, headers=_auth(owner_tok))
    assert r.status_code == 403

    # But an admin can, and the owner can then view the run.
    _, admin_tok = _user(SessionLocal, Role.admin, "admin2")
    started = client.post(
        f"/api/requests/{rid}/validation-runs", json={}, headers=_auth(admin_tok)
    )
    assert started.status_code == 202
    run_id = started.json()["id"]
    seen = client.get(f"/api/validation-runs/{run_id}", headers=_auth(owner_tok))
    assert seen.status_code == 200


def test_run_requires_ready_env(app_and_session):
    app, SessionLocal = app_and_session
    admin_id, admin_tok = _user(SessionLocal, Role.admin, "admin")
    _seed_default_pipeline(SessionLocal, admin_id)
    owner_id, _ = _user(SessionLocal, Role.requester, "owner")

    # Request with no env at all.
    db = SessionLocal()
    req = IntakeRequest(created_by_id=owner_id, status="submitted", payload={})
    db.add(req)
    db.commit()
    db.refresh(req)
    rid = req.id
    db.close()

    client = TestClient(app)
    r = client.post(f"/api/requests/{rid}/validation-runs", json={}, headers=_auth(admin_tok))
    assert r.status_code == 400


def test_artifacts_listed_and_downloadable(app_and_session):
    app, SessionLocal = app_and_session
    admin_id, admin_tok = _user(SessionLocal, Role.admin, "admin")
    _seed_default_pipeline(SessionLocal, admin_id)
    owner_id, _ = _user(SessionLocal, Role.requester, "owner")
    rid = _request_with_ready_env(SessionLocal, owner_id)

    client = TestClient(app)
    run_id = client.post(
        f"/api/requests/{rid}/validation-runs", json={}, headers=_auth(admin_tok)
    ).json()["id"]

    arts = client.get(f"/api/validation-runs/{run_id}/artifacts", headers=_auth(admin_tok)).json()
    # Two executors produced one artifact each (image-scan skipped → none).
    assert len(arts) == 2
    assert all("content" not in a for a in arts)

    art_id = arts[0]["id"]
    dl = client.get(f"/api/validation-artifacts/{art_id}/download", headers=_auth(admin_tok))
    assert dl.status_code == 200
    assert dl.content == b'{"ok": true}'
    assert "attachment" in dl.headers["content-disposition"]


def test_list_runs(app_and_session):
    app, SessionLocal = app_and_session
    admin_id, admin_tok = _user(SessionLocal, Role.admin, "admin")
    _seed_default_pipeline(SessionLocal, admin_id)
    owner_id, _ = _user(SessionLocal, Role.requester, "owner")
    rid = _request_with_ready_env(SessionLocal, owner_id)

    client = TestClient(app)
    client.post(f"/api/requests/{rid}/validation-runs", json={}, headers=_auth(admin_tok))
    client.post(f"/api/requests/{rid}/validation-runs", json={}, headers=_auth(admin_tok))

    runs = client.get(f"/api/requests/{rid}/validation-runs", headers=_auth(admin_tok)).json()
    assert len(runs) == 2
    # Newest first.
    assert runs[0]["id"] > runs[1]["id"]
