"""Unit tests for the validation pipeline parser + CRUD service (Chunk 2)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.domain.default_pipeline import DEFAULT_PIPELINE_NAME, DEFAULT_PIPELINE_YAML
from app.models.user import User
from app.repositories import validation_pipelines as repo
from app.services import validation_pipeline_service as svc


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _admin(db: Session) -> User:
    u = User(username="admin", email="a@b.c", password_hash="x", role="admin", is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Parser: happy path
# ---------------------------------------------------------------------------


def test_default_pipeline_yaml_parses() -> None:
    norm = svc.parse_and_validate(DEFAULT_PIPELINE_YAML)
    assert norm["name"] == DEFAULT_PIPELINE_NAME
    assert norm["failurePolicy"] == "warn"
    step_names = [s["name"] for s in norm["steps"]]
    assert step_names == ["workload-inventory", "kubernetes-security", "image-scan"]
    # Pipeline default policy applied where a step omits it (none do here, but
    # the security/image-scan steps explicitly block).
    by_name = {s["name"]: s for s in norm["steps"]}
    assert by_name["kubernetes-security"]["failurePolicy"] == "block"
    assert by_name["image-scan"]["failurePolicy"] == "block"
    assert by_name["workload-inventory"]["failurePolicy"] == "warn"


def test_step_defaults_filled_in() -> None:
    y = """
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: minimal
spec:
  steps:
    - name: inv
      type: builtin.workload_inventory
"""
    norm = svc.parse_and_validate(y)
    step = norm["steps"][0]
    assert step["enabled"] is True
    assert step["required"] is False
    assert step["dependsOn"] == []
    assert step["timeoutSeconds"] == 300  # default
    assert step["failurePolicy"] == "warn"  # inherits pipeline default
    assert step["displayName"] == "Workload Inventory"  # from registry
    assert norm["displayName"] == "minimal"  # falls back to name


# ---------------------------------------------------------------------------
# Parser: rejection cases
# ---------------------------------------------------------------------------


def test_reject_non_mapping() -> None:
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate("- just\n- a\n- list\n")
    assert ei.value.status_code == 400


def test_reject_bad_yaml() -> None:
    with pytest.raises(HTTPException):
        svc.parse_and_validate("apiVersion: : :\n  bad: [unclosed")


def test_reject_wrong_api_version() -> None:
    y = "apiVersion: foyre.ai/v2\nkind: ValidationPipeline\nmetadata:\n  name: x\nspec:\n  steps:\n    - name: a\n      type: builtin.workload_inventory\n"
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "apiVersion" in str(ei.value.detail)


def test_reject_wrong_kind() -> None:
    y = "apiVersion: foyre.ai/v1alpha1\nkind: Pipeline\nmetadata:\n  name: x\nspec:\n  steps:\n    - name: a\n      type: builtin.workload_inventory\n"
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "kind" in str(ei.value.detail)


def test_reject_bad_name() -> None:
    y = "apiVersion: foyre.ai/v1alpha1\nkind: ValidationPipeline\nmetadata:\n  name: Bad_Name\nspec:\n  steps:\n    - name: a\n      type: builtin.workload_inventory\n"
    with pytest.raises(HTTPException):
        svc.parse_and_validate(y)


def test_reject_empty_steps() -> None:
    y = "apiVersion: foyre.ai/v1alpha1\nkind: ValidationPipeline\nmetadata:\n  name: x\nspec:\n  steps: []\n"
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "non-empty" in str(ei.value.detail)


def test_reject_unknown_step_type() -> None:
    y = "apiVersion: foyre.ai/v1alpha1\nkind: ValidationPipeline\nmetadata:\n  name: x\nspec:\n  steps:\n    - name: a\n      type: builtin.does_not_exist\n"
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "Unknown step type" in str(ei.value.detail)


def test_planned_step_type_gives_helpful_message() -> None:
    y = "apiVersion: foyre.ai/v1alpha1\nkind: ValidationPipeline\nmetadata:\n  name: x\nspec:\n  steps:\n    - name: a\n      type: trivy.scan\n"
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "planned but not yet available" in str(ei.value.detail)


def test_reject_duplicate_step_names() -> None:
    y = """
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: x
spec:
  steps:
    - name: a
      type: builtin.workload_inventory
    - name: a
      type: builtin.kubernetes_security
"""
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "Duplicate step name" in str(ei.value.detail)


def test_reject_self_dependency() -> None:
    y = """
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: x
spec:
  steps:
    - name: a
      type: builtin.workload_inventory
      dependsOn: [a]
"""
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "itself" in str(ei.value.detail)


def test_reject_missing_dependency() -> None:
    y = """
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: x
spec:
  steps:
    - name: a
      type: builtin.workload_inventory
      dependsOn: [ghost]
"""
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "unknown step" in str(ei.value.detail)


def test_reject_dependency_cycle() -> None:
    y = """
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: x
spec:
  steps:
    - name: a
      type: builtin.workload_inventory
      dependsOn: [b]
    - name: b
      type: builtin.kubernetes_security
      dependsOn: [a]
"""
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "cycle" in str(ei.value.detail)


def test_reject_bad_failure_policy() -> None:
    y = """
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: x
spec:
  steps:
    - name: a
      type: builtin.workload_inventory
      failurePolicy: explode
"""
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "failurePolicy" in str(ei.value.detail)


def test_reject_timeout_out_of_bounds() -> None:
    y = """
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: x
spec:
  steps:
    - name: a
      type: builtin.workload_inventory
      timeoutSeconds: 99999
"""
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "timeoutSeconds" in str(ei.value.detail)


def test_custom_job_requires_image() -> None:
    y = """
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: x
spec:
  steps:
    - name: company-check
      type: custom.kubernetes_job
      config:
        command: ["/app/check"]
"""
    with pytest.raises(HTTPException) as ei:
        svc.parse_and_validate(y)
    assert "config.image" in str(ei.value.detail)


def test_custom_job_with_image_ok() -> None:
    y = """
apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: x
spec:
  steps:
    - name: company-check
      type: custom.kubernetes_job
      config:
        image: registry.example.com/checker:latest
"""
    norm = svc.parse_and_validate(y)
    assert norm["steps"][0]["config"]["image"] == "registry.example.com/checker:latest"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_and_get(db: Session) -> None:
    admin = _admin(db)
    pipe = svc.create_pipeline(db, admin, definition_yaml=DEFAULT_PIPELINE_YAML, is_default=True)
    assert pipe.name == DEFAULT_PIPELINE_NAME
    assert pipe.version == 1
    assert pipe.is_default is True
    fetched = svc.get_pipeline(db, pipe.id)
    assert fetched.id == pipe.id


def test_create_duplicate_name_conflicts(db: Session) -> None:
    admin = _admin(db)
    svc.create_pipeline(db, admin, definition_yaml=DEFAULT_PIPELINE_YAML)
    with pytest.raises(HTTPException) as ei:
        svc.create_pipeline(db, admin, definition_yaml=DEFAULT_PIPELINE_YAML)
    assert ei.value.status_code == 409


def test_update_bumps_version(db: Session) -> None:
    admin = _admin(db)
    pipe = svc.create_pipeline(db, admin, definition_yaml=DEFAULT_PIPELINE_YAML)
    assert pipe.version == 1
    # Re-save same definition → version increments.
    updated = svc.update_pipeline(
        db, admin, pipe.id, definition_yaml=DEFAULT_PIPELINE_YAML
    )
    assert updated.version == 2


def test_update_enable_disable_without_definition(db: Session) -> None:
    admin = _admin(db)
    pipe = svc.create_pipeline(db, admin, definition_yaml=DEFAULT_PIPELINE_YAML)
    updated = svc.update_pipeline(db, admin, pipe.id, enabled=False)
    assert updated.enabled is False
    assert updated.version == 1  # version unchanged when only toggling enabled


def test_set_default_clears_others(db: Session) -> None:
    admin = _admin(db)
    a = svc.create_pipeline(
        db, admin, definition_yaml=DEFAULT_PIPELINE_YAML.replace(DEFAULT_PIPELINE_NAME, "pipe-a"), is_default=True
    )
    b_yaml = DEFAULT_PIPELINE_YAML.replace(DEFAULT_PIPELINE_NAME, "pipe-b")
    b = svc.create_pipeline(db, admin, definition_yaml=b_yaml)
    svc.set_default(db, b.id)
    db.refresh(a)
    db.refresh(b)
    assert a.is_default is False
    assert b.is_default is True


def test_set_default_rejects_disabled(db: Session) -> None:
    admin = _admin(db)
    pipe = svc.create_pipeline(db, admin, definition_yaml=DEFAULT_PIPELINE_YAML)
    svc.update_pipeline(db, admin, pipe.id, enabled=False)
    with pytest.raises(HTTPException) as ei:
        svc.set_default(db, pipe.id)
    assert ei.value.status_code == 400


def test_delete(db: Session) -> None:
    admin = _admin(db)
    pipe = svc.create_pipeline(db, admin, definition_yaml=DEFAULT_PIPELINE_YAML)
    svc.delete_pipeline(db, pipe.id)
    assert repo.get(db, pipe.id) is None


def test_get_missing_404(db: Session) -> None:
    with pytest.raises(HTTPException) as ei:
        svc.get_pipeline(db, 9999)
    assert ei.value.status_code == 404


def test_resolve_for_run_uses_default(db: Session) -> None:
    admin = _admin(db)
    pipe = svc.create_pipeline(db, admin, definition_yaml=DEFAULT_PIPELINE_YAML, is_default=True)
    resolved = svc.resolve_for_run(db, None)
    assert resolved.id == pipe.id


def test_resolve_for_run_no_default_errors(db: Session) -> None:
    with pytest.raises(HTTPException) as ei:
        svc.resolve_for_run(db, None)
    assert ei.value.status_code == 400


def test_resolve_for_run_disabled_errors(db: Session) -> None:
    admin = _admin(db)
    pipe = svc.create_pipeline(db, admin, definition_yaml=DEFAULT_PIPELINE_YAML)
    svc.update_pipeline(db, admin, pipe.id, enabled=False)
    with pytest.raises(HTTPException) as ei:
        svc.resolve_for_run(db, pipe.id)
    assert ei.value.status_code == 400
