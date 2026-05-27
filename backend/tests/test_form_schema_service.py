"""Unit tests for the configurable form schema service."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.domain.form_schema import CORE_FIELD_NAMES, default_schema
from app.models.user import User  # noqa: F401 -- needed for relationship configure
from app.services import form_schema_service


@pytest.fixture
def db() -> Session:
    """Fresh in-memory SQLite session, isolated per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_admin(db: Session) -> User:
    """Persist a minimal admin user for `updated_by` linkage."""
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash="x",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_get_returns_default_when_uncustomized(db: Session) -> None:
    sections = form_schema_service.get_active_sections(db)
    field_names = {f["name"] for s in sections for f in s["fields"]}
    assert CORE_FIELD_NAMES <= field_names
    for section in sections:
        for f in section["fields"]:
            assert f["source"] == "core"


def test_save_with_custom_field_round_trips(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    schema["sections"][0]["fields"].append(
        {
            "name": "cost_center",
            "label": "Cost center",
            "type": "text",
            "required": True,
        }
    )
    form_schema_service.save(db, admin, schema)

    sections = form_schema_service.get_active_sections(db)
    found = next(
        (f for s in sections for f in s["fields"] if f["name"] == "cost_center"),
        None,
    )
    assert found is not None
    assert found["source"] == "custom"
    assert found["required"] is True
    assert found["label"] == "Cost center"


def test_admin_cannot_remove_core_field(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    # Strip out the entire data_and_risk section, which contains many core fields.
    schema["sections"] = [s for s in schema["sections"] if s["id"] != "data_and_risk"]
    with pytest.raises(HTTPException) as ei:
        form_schema_service.save(db, admin, schema)
    assert ei.value.status_code == 400
    assert "built-in" in ei.value.detail.lower() or "missing" in ei.value.detail.lower()


def test_admin_cannot_change_core_field_type(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    # Try to turn `application_name` into a checkbox.
    for s in schema["sections"]:
        for f in s["fields"]:
            if f["name"] == "application_name":
                f["type"] = "boolean"
                f["required"] = False

    form_schema_service.save(db, admin, schema)
    # Even though we sent boolean, the persisted shape canonicalizes to text.
    sections = form_schema_service.get_active_sections(db)
    f = next(f for s in sections for f in s["fields"] if f["name"] == "application_name")
    assert f["type"] == "text"
    assert f["required"] is True


def test_admin_can_relabel_and_resection_core_field(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    moved = None
    for s in schema["sections"]:
        if s["id"] == "basics":
            for f in list(s["fields"]):
                if f["name"] == "team":
                    moved = dict(f)
                    moved["label"] = "Cost center / department"
                    s["fields"].remove(f)
    assert moved is not None
    schema["sections"].append(
        {"id": "finance", "title": "Finance", "fields": [moved]}
    )

    form_schema_service.save(db, admin, schema)
    sections = form_schema_service.get_active_sections(db)
    finance = next(s for s in sections if s["id"] == "finance")
    team_field = next(f for f in finance["fields"] if f["name"] == "team")
    assert team_field["label"] == "Cost center / department"
    assert team_field["source"] == "core"


def test_custom_field_name_validation(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    schema["sections"][0]["fields"].append(
        {"name": "Bad Name!", "label": "Bad", "type": "text"}
    )
    with pytest.raises(HTTPException) as ei:
        form_schema_service.save(db, admin, schema)
    assert ei.value.status_code == 400


def test_custom_field_cannot_use_core_name(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    schema["sections"][0]["fields"].append(
        {"name": "application_name", "label": "dup", "type": "text"}
    )
    with pytest.raises(HTTPException):
        form_schema_service.save(db, admin, schema)


def test_custom_select_must_have_options(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    schema["sections"][0]["fields"].append(
        {"name": "tier", "label": "Tier", "type": "select", "options": []}
    )
    with pytest.raises(HTTPException) as ei:
        form_schema_service.save(db, admin, schema)
    assert "option" in ei.value.detail.lower()


def test_reset_drops_customization(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    schema["sections"][0]["fields"].append(
        {"name": "cost_center", "label": "Cost center", "type": "text"}
    )
    form_schema_service.save(db, admin, schema)
    form_schema_service.reset(db)

    sections = form_schema_service.get_active_sections(db)
    names = {f["name"] for s in sections for f in s["fields"]}
    assert "cost_center" not in names


def test_validate_custom_payload_required_missing(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    schema["sections"][0]["fields"].append(
        {"name": "cost_center", "label": "Cost center", "type": "text", "required": True}
    )
    form_schema_service.save(db, admin, schema)

    result = form_schema_service.validate_custom_payload(db, {})
    assert any(e["loc"] == ["cost_center"] for e in result["errors"])


def test_validate_custom_payload_select_must_be_in_options(db: Session) -> None:
    admin = _make_admin(db)
    schema = {"sections": default_schema()}
    schema["sections"][0]["fields"].append(
        {
            "name": "tier",
            "label": "Tier",
            "type": "select",
            "required": True,
            "options": [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
        }
    )
    form_schema_service.save(db, admin, schema)

    bad = form_schema_service.validate_custom_payload(db, {"tier": "c"})
    assert any(e["loc"] == ["tier"] for e in bad["errors"])

    good = form_schema_service.validate_custom_payload(db, {"tier": "a"})
    assert good["errors"] == []
