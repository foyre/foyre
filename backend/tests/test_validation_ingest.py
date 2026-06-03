"""Tests for the per-run ingest token + ingest endpoint (Chunk 3)."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.tokens import issue_token
from app.config import settings
from app.db import Base, get_db
from app.domain.enums import Role, ValidationRunStatus
from app.main import create_app
from app.models.request import IntakeRequest
from app.models.user import User
from app.models.validation_run import ValidationRun
from app.repositories import (
    validation_artifacts as artifacts_repo,
    validation_ingest_records as ingest_repo,
)
from app.validation.ingest_token import issue_ingest_token, verify_ingest_token


# ---------------------------------------------------------------------------
# Token unit tests
# ---------------------------------------------------------------------------


def test_ingest_token_round_trips():
    tok = issue_ingest_token(run_id=7, step_name="custom-check", step_result_id=3)
    claims = verify_ingest_token(tok)
    assert claims is not None
    assert claims["sub"] == "7"
    assert claims["step"] == "custom-check"
    assert claims["srid"] == 3


def test_user_token_rejected_as_ingest():
    user_tok = issue_token(subject="1", extra={"role": "admin"})
    assert verify_ingest_token(user_tok) is None  # wrong/no scope


def test_expired_ingest_token_rejected():
    now = datetime.now(tz=timezone.utc)
    expired = jwt.encode(
        {
            "sub": "1",
            "scope": "validation-ingest",
            "step": "s",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert verify_ingest_token(expired) is None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def app_and_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    app = create_app()

    def _override():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override
    return app, SessionLocal


def _make_run(SessionLocal, status=ValidationRunStatus.running) -> int:
    s = SessionLocal()
    owner = User(username="o", email="o@e.com", password_hash="x", role="requester", is_active=True)
    s.add(owner)
    s.commit()
    s.refresh(owner)
    req = IntakeRequest(created_by_id=owner.id, status="under_review", payload={})
    s.add(req)
    s.commit()
    s.refresh(req)
    run = ValidationRun(
        request_id=req.id,
        pipeline_name="p",
        pipeline_version=1,
        pipeline_definition_json={"steps": []},
        status=status.value,
    )
    s.add(run)
    s.commit()
    rid = run.id
    s.close()
    return rid


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def test_ingest_stores_artifacts_and_record(app_and_session):
    app, SessionLocal = app_and_session
    rid = _make_run(SessionLocal)
    tok = issue_ingest_token(run_id=rid, step_name="custom-check")
    client = TestClient(app)

    r = client.post(
        f"/api/validation-ingest/{rid}",
        json={
            "exit_code": 0,
            "job_state": "succeeded",
            "result": {"status": "passed", "summary": "ok"},
            "artifacts": [
                {"name": "report.json", "artifact_type": "json", "content_b64": _b64('{"x":1}')},
                {"name": "scan.txt", "content_b64": _b64("hello")},
            ],
        },
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stored"] == 2
    assert body["record_id"] is not None

    db = SessionLocal()
    try:
        arts = artifacts_repo.list_for_run(db, rid)
        assert {a.artifact_name for a in arts} == {"report.json", "scan.txt"}
        # Unknown type coerced to "text".
        assert next(a for a in arts if a.artifact_name == "scan.txt").artifact_type == "text"
        rec = ingest_repo.latest_for_step(db, rid, "custom-check")
        assert rec.result_json == {"status": "passed", "summary": "ok"}
        assert rec.exit_code == 0
    finally:
        db.close()


def test_ingest_rejects_user_bearer(app_and_session):
    app, SessionLocal = app_and_session
    rid = _make_run(SessionLocal)
    user_tok = issue_token(subject="1", extra={"role": "admin"})
    client = TestClient(app)
    r = client.post(
        f"/api/validation-ingest/{rid}",
        json={"artifacts": []},
        headers={"Authorization": f"Bearer {user_tok}"},
    )
    assert r.status_code == 401


def test_ingest_rejects_token_for_other_run(app_and_session):
    app, SessionLocal = app_and_session
    rid = _make_run(SessionLocal)
    tok = issue_ingest_token(run_id=rid + 999, step_name="s")
    client = TestClient(app)
    r = client.post(
        f"/api/validation-ingest/{rid}",
        json={"artifacts": []},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 403


def test_ingest_rejects_when_run_terminal(app_and_session):
    app, SessionLocal = app_and_session
    rid = _make_run(SessionLocal, status=ValidationRunStatus.passed)
    tok = issue_ingest_token(run_id=rid, step_name="s")
    client = TestClient(app)
    r = client.post(
        f"/api/validation-ingest/{rid}",
        json={"artifacts": []},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 409


def test_ingest_enforces_per_file_size_cap(app_and_session, monkeypatch):
    from app.services import validation_ingest_service

    monkeypatch.setattr(validation_ingest_service, "MAX_ARTIFACT_BYTES", 8)
    app, SessionLocal = app_and_session
    rid = _make_run(SessionLocal)
    tok = issue_ingest_token(run_id=rid, step_name="s")
    client = TestClient(app)
    r = client.post(
        f"/api/validation-ingest/{rid}",
        json={
            "artifacts": [
                {"name": "ok.txt", "content_b64": _b64("tiny")},
                {"name": "big.txt", "content_b64": _b64("way too large content")},
            ]
        },
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stored"] == 1
    assert any(o["name"] == "big.txt" and "too large" in o["reason"] for o in body["omitted"])


def test_ingest_enforces_file_count_cap(app_and_session, monkeypatch):
    from app.services import validation_ingest_service

    monkeypatch.setattr(validation_ingest_service, "MAX_ARTIFACTS_PER_RUN", 1)
    app, SessionLocal = app_and_session
    rid = _make_run(SessionLocal)
    tok = issue_ingest_token(run_id=rid, step_name="s")
    client = TestClient(app)
    r = client.post(
        f"/api/validation-ingest/{rid}",
        json={
            "artifacts": [
                {"name": "a.txt", "content_b64": _b64("a")},
                {"name": "b.txt", "content_b64": _b64("b")},
            ]
        },
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stored"] == 1
    assert any("count" in o["reason"] for o in body["omitted"])


def test_ingest_invalid_base64_omitted(app_and_session):
    app, SessionLocal = app_and_session
    rid = _make_run(SessionLocal)
    tok = issue_ingest_token(run_id=rid, step_name="s")
    client = TestClient(app)
    r = client.post(
        f"/api/validation-ingest/{rid}",
        json={"artifacts": [{"name": "bad", "content_b64": "!!!not base64!!!"}]},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    assert r.json()["stored"] == 0
    assert r.json()["omitted"][0]["reason"] == "invalid base64"
