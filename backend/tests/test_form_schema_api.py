"""End-to-end checks of the admin form-schema endpoints + custom-field submit flow."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.passwords import hash_password
from app.auth.tokens import issue_token
from app.db import Base, get_db
from app.domain.enums import Role
from app.main import create_app
from app.models.user import User


@pytest.fixture
def app_and_session():
    # StaticPool + shared in-memory URI so every session sees the same DB.
    # Without this, each new connection gets its own private SQLite memory DB
    # and tables created on one are invisible to the next.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    app = create_app()

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return app, SessionLocal


def _make_user(SessionLocal, role: Role, username: str) -> tuple[User, str]:
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
    return user, token


def test_admin_get_returns_bundle(app_and_session) -> None:
    app, SessionLocal = app_and_session
    _, token = _make_user(SessionLocal, Role.admin, "admin1")
    client = TestClient(app)
    r = client.get(
        "/api/admin/form-schema", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert "current" in body
    assert "default" in body
    assert "core_field_names" in body
    assert "application_name" in body["core_field_names"]
    # By default, nothing customized yet.
    assert body["current"]["is_customized"] is False


def test_non_admin_cannot_read_admin_endpoint(app_and_session) -> None:
    app, SessionLocal = app_and_session
    _, token = _make_user(SessionLocal, Role.requester, "req1")
    client = TestClient(app)
    r = client.get(
        "/api/admin/form-schema", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


def test_save_with_custom_field_visible_in_meta(app_and_session) -> None:
    app, SessionLocal = app_and_session
    _, token = _make_user(SessionLocal, Role.admin, "admin2")
    client = TestClient(app)

    # Read default to use as base.
    base = client.get(
        "/api/admin/form-schema", headers={"Authorization": f"Bearer {token}"}
    ).json()
    sections = base["default"]["sections"]
    sections[-1]["fields"].append(
        {
            "name": "cost_center",
            "label": "Cost center",
            "type": "text",
            "required": True,
        }
    )
    r = client.put(
        "/api/admin/form-schema",
        json={"sections": sections},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["current"]["is_customized"] is True

    # The public meta endpoint should now expose the custom field.
    meta = client.get(
        "/api/meta/form-schema", headers={"Authorization": f"Bearer {token}"}
    ).json()
    field_names = [f["name"] for s in meta["sections"] for f in s["fields"]]
    assert "cost_center" in field_names


def test_submit_blocked_when_required_custom_field_missing(app_and_session) -> None:
    app, SessionLocal = app_and_session
    admin, admin_token = _make_user(SessionLocal, Role.admin, "admin3")
    requester, req_token = _make_user(SessionLocal, Role.requester, "req2")
    client = TestClient(app)

    # Admin adds a required custom field.
    base = client.get(
        "/api/admin/form-schema", headers={"Authorization": f"Bearer {admin_token}"}
    ).json()
    sections = base["default"]["sections"]
    sections[-1]["fields"].append(
        {
            "name": "cost_center",
            "label": "Cost center",
            "type": "text",
            "required": True,
        }
    )
    client.put(
        "/api/admin/form-schema",
        json={"sections": sections},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Requester creates a draft missing the new required field, then submits.
    payload = {
        "application_name": "Test App",
        "business_owner": "Owner",
        "technical_owner": "Tech",
        "team": "platform",
        "description": "x",
        "environment": "dev",
        "workload_type": "chatbot",
        "handles_sensitive_data": "no",
        "data_classification": "internal",
    }
    r = client.post(
        "/api/requests",
        json={"payload": payload},
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    r = client.post(
        f"/api/requests/{rid}/submit",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert r.status_code == 422
    errors = r.json()["detail"]["errors"]
    assert any(e["loc"] == ["cost_center"] for e in errors)

    # Filling it in lets the submit succeed.
    payload["cost_center"] = "CC-123"
    client.patch(
        f"/api/requests/{rid}",
        json={"payload": payload},
        headers={"Authorization": f"Bearer {req_token}"},
    )
    r = client.post(
        f"/api/requests/{rid}/submit",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert r.status_code == 200, r.text
    out = r.json()
    # Custom value should round-trip through the payload column.
    assert out["payload"]["cost_center"] == "CC-123"


def test_reset_drops_customization_via_api(app_and_session) -> None:
    app, SessionLocal = app_and_session
    _, token = _make_user(SessionLocal, Role.admin, "admin4")
    client = TestClient(app)

    base = client.get(
        "/api/admin/form-schema", headers={"Authorization": f"Bearer {token}"}
    ).json()
    sections = base["default"]["sections"]
    sections[-1]["fields"].append(
        {"name": "cost_center", "label": "Cost center", "type": "text"}
    )
    client.put(
        "/api/admin/form-schema",
        json={"sections": sections},
        headers={"Authorization": f"Bearer {token}"},
    )

    r = client.post(
        "/api/admin/form-schema/reset",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["current"]["is_customized"] is False
    names = [
        f["name"]
        for s in r.json()["current"]["sections"]
        for f in s["fields"]
    ]
    assert "cost_center" not in names
