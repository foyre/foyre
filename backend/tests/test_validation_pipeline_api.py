"""End-to-end checks of the validation pipeline API + seed idempotency (Chunk 2)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.passwords import hash_password
from app.auth.tokens import issue_token
from app.db import Base, get_db
from app.domain.default_pipeline import DEFAULT_PIPELINE_NAME, DEFAULT_PIPELINE_YAML
from app.domain.enums import Role
from app.main import create_app
from app.models.user import User


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

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return app, SessionLocal


def _make_user(SessionLocal, role: Role, username: str) -> str:
    db = SessionLocal()
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=hash_password("x"),
        role=role.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = issue_token(subject=str(user.id), extra={"role": user.role})
    db.close()
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_requester_cannot_list_pipelines(app_and_session) -> None:
    app, SessionLocal = app_and_session
    token = _make_user(SessionLocal, Role.requester, "req")
    client = TestClient(app)
    r = client.get("/api/validation/pipelines", headers=_auth(token))
    assert r.status_code == 403


def test_reviewer_can_list_but_not_create(app_and_session) -> None:
    app, SessionLocal = app_and_session
    token = _make_user(SessionLocal, Role.reviewer, "rev")
    client = TestClient(app)
    assert client.get("/api/validation/pipelines", headers=_auth(token)).status_code == 200
    r = client.post(
        "/api/validation/pipelines",
        json={"definition_yaml": DEFAULT_PIPELINE_YAML},
        headers=_auth(token),
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# CRUD lifecycle
# ---------------------------------------------------------------------------


def test_admin_pipeline_lifecycle(app_and_session) -> None:
    app, SessionLocal = app_and_session
    token = _make_user(SessionLocal, Role.admin, "admin")
    client = TestClient(app)
    h = _auth(token)

    # Create.
    r = client.post(
        "/api/validation/pipelines",
        json={"definition_yaml": DEFAULT_PIPELINE_YAML, "is_default": True},
        headers=h,
    )
    assert r.status_code == 201, r.text
    created = r.json()
    pid = created["id"]
    assert created["name"] == DEFAULT_PIPELINE_NAME
    assert created["is_default"] is True
    assert len(created["definition_json"]["steps"]) == 3

    # List (summary projection — no heavy definition).
    r = client.get("/api/validation/pipelines", headers=h)
    assert r.status_code == 200
    listed = r.json()
    assert len(listed) == 1
    assert "definition_json" not in listed[0]

    # Get one.
    r = client.get(f"/api/validation/pipelines/{pid}", headers=h)
    assert r.status_code == 200
    assert r.json()["definition_json"]["name"] == DEFAULT_PIPELINE_NAME

    # Update → version bump.
    r = client.put(
        f"/api/validation/pipelines/{pid}",
        json={"definition_yaml": DEFAULT_PIPELINE_YAML},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2

    # Delete.
    assert client.delete(f"/api/validation/pipelines/{pid}", headers=h).status_code == 204
    assert client.get(f"/api/validation/pipelines/{pid}", headers=h).status_code == 404


def test_create_invalid_yaml_returns_400(app_and_session) -> None:
    app, SessionLocal = app_and_session
    token = _make_user(SessionLocal, Role.admin, "admin")
    client = TestClient(app)
    r = client.post(
        "/api/validation/pipelines",
        json={"definition_yaml": "kind: nope\n"},
        headers=_auth(token),
    )
    assert r.status_code == 400


def test_validate_endpoint_reports_invalid_without_4xx(app_and_session) -> None:
    app, SessionLocal = app_and_session
    token = _make_user(SessionLocal, Role.admin, "admin")
    client = TestClient(app)

    ok = client.post(
        "/api/validation/pipelines/validate",
        json={"definition_yaml": DEFAULT_PIPELINE_YAML},
        headers=_auth(token),
    )
    assert ok.status_code == 200
    assert ok.json()["valid"] is True
    assert ok.json()["normalized"]["name"] == DEFAULT_PIPELINE_NAME

    bad = client.post(
        "/api/validation/pipelines/validate",
        json={"definition_yaml": "apiVersion: wrong\nkind: ValidationPipeline\n"},
        headers=_auth(token),
    )
    assert bad.status_code == 200
    assert bad.json()["valid"] is False
    assert bad.json()["error"]


def test_set_default_via_api(app_and_session) -> None:
    app, SessionLocal = app_and_session
    token = _make_user(SessionLocal, Role.admin, "admin")
    client = TestClient(app)
    h = _auth(token)

    a = client.post(
        "/api/validation/pipelines",
        json={"definition_yaml": DEFAULT_PIPELINE_YAML.replace(DEFAULT_PIPELINE_NAME, "pipe-a"), "is_default": True},
        headers=h,
    ).json()
    b = client.post(
        "/api/validation/pipelines",
        json={"definition_yaml": DEFAULT_PIPELINE_YAML.replace(DEFAULT_PIPELINE_NAME, "pipe-b")},
        headers=h,
    ).json()

    r = client.post(f"/api/validation/pipelines/{b['id']}/set-default", headers=h)
    assert r.status_code == 200
    assert r.json()["is_default"] is True
    # a is no longer default.
    assert client.get(f"/api/validation/pipelines/{a['id']}", headers=h).json()["is_default"] is False


# ---------------------------------------------------------------------------
# Seed idempotency
# ---------------------------------------------------------------------------


def test_seed_default_pipeline_idempotent(app_and_session) -> None:
    """Running the seed helper twice creates the default pipeline once."""
    app, SessionLocal = app_and_session
    from app.seed import _seed_default_pipeline

    db = SessionLocal()
    try:
        _seed_default_pipeline(db, admin=None)
        _seed_default_pipeline(db, admin=None)  # second run is a no-op
    finally:
        db.close()

    from app.repositories import validation_pipelines as repo

    db = SessionLocal()
    try:
        rows = repo.list_all(db)
        names = [p.name for p in rows]
        assert names.count(DEFAULT_PIPELINE_NAME) == 1
        # Seeded as the default since none existed.
        assert repo.get_default(db).name == DEFAULT_PIPELINE_NAME
    finally:
        db.close()
