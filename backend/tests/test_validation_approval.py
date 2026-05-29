"""Approval-gate tests (Chunk 5): policy resolution, gate evaluation, and
the end-to-end approve/override flow through the status endpoint.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.passwords import hash_password
from app.auth.tokens import issue_token
from app.db import Base, get_db
from app.domain.enums import ApprovalImpact, Role, ValidationRunStatus
from app.main import create_app
from app.models.request import IntakeRequest
from app.models.user import User
from app.models.validation_run import ValidationRun
from app.services import validation_approval_service, validation_policy_service


# ---------------------------------------------------------------------------
# Unit: policy + gate
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _admin(db: Session) -> User:
    u = User(username="admin", email="a@b.c", password_hash="x", role="admin", is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _request(db: Session, owner_id: int, status: str = "under_review") -> IntakeRequest:
    r = IntakeRequest(created_by_id=owner_id, status=status, payload={})
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _run(db: Session, request_id: int, status: ValidationRunStatus, impact: ApprovalImpact) -> ValidationRun:
    run = ValidationRun(
        request_id=request_id,
        pipeline_name="p",
        pipeline_version=1,
        pipeline_definition_json={"steps": []},
        status=status.value,
        approval_impact=impact.value,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def test_default_policy_does_not_block_without_run(db):
    admin = _admin(db)
    req = _request(db, admin.id)
    gate = validation_approval_service.evaluate(db, req.id)
    assert gate.blocked is False
    assert gate.missing_validation is True
    assert gate.override_allowed is True  # default


def test_require_validation_blocks_without_run(db):
    admin = _admin(db)
    validation_policy_service.update(db, admin, require_validation_before_approval=True)
    req = _request(db, admin.id)
    gate = validation_approval_service.evaluate(db, req.id)
    assert gate.blocked is True
    assert "required" in gate.reason.lower()


def test_blocking_run_blocks(db):
    admin = _admin(db)
    req = _request(db, admin.id)
    _run(db, req.id, ValidationRunStatus.failed, ApprovalImpact.blocked)
    gate = validation_approval_service.evaluate(db, req.id)
    assert gate.blocked is True
    assert gate.impact == ApprovalImpact.blocked


def test_warning_run_does_not_block(db):
    admin = _admin(db)
    req = _request(db, admin.id)
    _run(db, req.id, ValidationRunStatus.warning, ApprovalImpact.warning)
    gate = validation_approval_service.evaluate(db, req.id)
    assert gate.blocked is False
    assert gate.impact == ApprovalImpact.warning


def test_block_disabled_by_policy(db):
    admin = _admin(db)
    validation_policy_service.update(db, admin, block_approval_on_failed_validation=False)
    req = _request(db, admin.id)
    _run(db, req.id, ValidationRunStatus.failed, ApprovalImpact.blocked)
    gate = validation_approval_service.evaluate(db, req.id)
    assert gate.blocked is False


def test_latest_run_wins(db):
    admin = _admin(db)
    req = _request(db, admin.id)
    _run(db, req.id, ValidationRunStatus.failed, ApprovalImpact.blocked)
    _run(db, req.id, ValidationRunStatus.passed, ApprovalImpact.none)  # newer
    gate = validation_approval_service.evaluate(db, req.id)
    assert gate.blocked is False


# ---------------------------------------------------------------------------
# End-to-end via the status endpoint
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


def _mk_user(SessionLocal, role: Role, username: str) -> tuple[int, str]:
    s = SessionLocal()
    u = User(username=username, email=f"{username}@e.com", password_hash=hash_password("x"), role=role.value, is_active=True)
    s.add(u)
    s.commit()
    s.refresh(u)
    uid, tok = u.id, issue_token(subject=str(u.id), extra={"role": u.role})
    s.close()
    return uid, tok


def _mk_request_under_review(SessionLocal, owner_id: int) -> int:
    s = SessionLocal()
    r = IntakeRequest(created_by_id=owner_id, status="under_review", payload={})
    s.add(r)
    s.commit()
    s.refresh(r)
    rid = r.id
    s.close()
    return rid


def _add_blocking_run(SessionLocal, request_id: int):
    s = SessionLocal()
    run = ValidationRun(
        request_id=request_id,
        pipeline_name="default",
        pipeline_version=1,
        pipeline_definition_json={"steps": []},
        status=ValidationRunStatus.failed.value,
        approval_impact=ApprovalImpact.blocked.value,
    )
    s.add(run)
    s.commit()
    s.close()


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_approve_blocked_returns_409(app_and_session):
    app, SessionLocal = app_and_session
    owner_id, _ = _mk_user(SessionLocal, Role.requester, "owner")
    _, rev = _mk_user(SessionLocal, Role.reviewer, "rev")
    rid = _mk_request_under_review(SessionLocal, owner_id)
    _add_blocking_run(SessionLocal, rid)

    client = TestClient(app)
    r = client.post(
        f"/api/requests/{rid}/status", json={"new_status": "approved"}, headers=_auth(rev)
    )
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["approval_impact"] == "blocked"
    assert detail["override_allowed"] is True


def test_override_requires_reason(app_and_session):
    app, SessionLocal = app_and_session
    owner_id, _ = _mk_user(SessionLocal, Role.requester, "owner")
    _, rev = _mk_user(SessionLocal, Role.reviewer, "rev")
    rid = _mk_request_under_review(SessionLocal, owner_id)
    _add_blocking_run(SessionLocal, rid)

    client = TestClient(app)
    r = client.post(
        f"/api/requests/{rid}/status",
        json={"new_status": "approved", "override_validation": True},
        headers=_auth(rev),
    )
    assert r.status_code == 400


def test_override_with_reason_approves(app_and_session):
    app, SessionLocal = app_and_session
    owner_id, _ = _mk_user(SessionLocal, Role.requester, "owner")
    _, rev = _mk_user(SessionLocal, Role.reviewer, "rev")
    rid = _mk_request_under_review(SessionLocal, owner_id)
    _add_blocking_run(SessionLocal, rid)

    client = TestClient(app)
    r = client.post(
        f"/api/requests/{rid}/status",
        json={
            "new_status": "approved",
            "override_validation": True,
            "override_reason": "Risk accepted by security lead.",
        },
        headers=_auth(rev),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # An override event is recorded in history.
    hist = client.get(f"/api/requests/{rid}/history", headers=_auth(rev)).json()
    assert any(e["event_type"] == "validation_override_used" for e in hist)


def test_override_disabled_by_policy_403(app_and_session):
    app, SessionLocal = app_and_session
    admin_id, admin = _mk_user(SessionLocal, Role.admin, "admin")
    owner_id, _ = _mk_user(SessionLocal, Role.requester, "owner")
    _, rev = _mk_user(SessionLocal, Role.reviewer, "rev")
    rid = _mk_request_under_review(SessionLocal, owner_id)
    _add_blocking_run(SessionLocal, rid)

    client = TestClient(app)
    # Admin disables override.
    assert client.put(
        "/api/admin/validation/policy",
        json={"allow_validation_override": False},
        headers=_auth(admin),
    ).status_code == 200

    r = client.post(
        f"/api/requests/{rid}/status",
        json={"new_status": "approved", "override_validation": True, "override_reason": "x"},
        headers=_auth(rev),
    )
    assert r.status_code == 403


def test_approve_succeeds_when_run_passed(app_and_session):
    app, SessionLocal = app_and_session
    owner_id, _ = _mk_user(SessionLocal, Role.requester, "owner")
    _, rev = _mk_user(SessionLocal, Role.reviewer, "rev")
    rid = _mk_request_under_review(SessionLocal, owner_id)
    # A passing run → no block.
    s = SessionLocal()
    s.add(
        ValidationRun(
            request_id=rid,
            pipeline_name="p",
            pipeline_version=1,
            pipeline_definition_json={"steps": []},
            status=ValidationRunStatus.passed.value,
            approval_impact=ApprovalImpact.none.value,
        )
    )
    s.commit()
    s.close()

    client = TestClient(app)
    r = client.post(
        f"/api/requests/{rid}/status", json={"new_status": "approved"}, headers=_auth(rev)
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_reject_not_gated(app_and_session):
    """The gate only applies to approval — rejecting a blocking-run request works."""
    app, SessionLocal = app_and_session
    owner_id, _ = _mk_user(SessionLocal, Role.requester, "owner")
    _, rev = _mk_user(SessionLocal, Role.reviewer, "rev")
    rid = _mk_request_under_review(SessionLocal, owner_id)
    _add_blocking_run(SessionLocal, rid)

    client = TestClient(app)
    r = client.post(
        f"/api/requests/{rid}/status", json={"new_status": "rejected"}, headers=_auth(rev)
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


# ---------------------------------------------------------------------------
# Policy + approval-gate endpoints
# ---------------------------------------------------------------------------


def test_policy_crud_admin_only(app_and_session):
    app, SessionLocal = app_and_session
    _, admin = _mk_user(SessionLocal, Role.admin, "admin")
    _, rev = _mk_user(SessionLocal, Role.reviewer, "rev")
    client = TestClient(app)

    assert client.get("/api/admin/validation/policy", headers=_auth(rev)).status_code == 403
    got = client.get("/api/admin/validation/policy", headers=_auth(admin))
    assert got.status_code == 200
    # Defaults surfaced even with no row.
    assert got.json()["block_approval_on_failed_validation"] is True

    upd = client.put(
        "/api/admin/validation/policy",
        json={"require_validation_before_approval": True},
        headers=_auth(admin),
    )
    assert upd.status_code == 200
    assert upd.json()["require_validation_before_approval"] is True


def test_approval_gate_endpoint(app_and_session):
    app, SessionLocal = app_and_session
    owner_id, owner = _mk_user(SessionLocal, Role.requester, "owner")
    rid = _mk_request_under_review(SessionLocal, owner_id)
    _add_blocking_run(SessionLocal, rid)

    client = TestClient(app)
    r = client.get(f"/api/requests/{rid}/validation-approval", headers=_auth(owner))
    assert r.status_code == 200
    body = r.json()
    assert body["blocked"] is True
    assert body["impact"] == "blocked"
    assert body["latest_run_id"] is not None
