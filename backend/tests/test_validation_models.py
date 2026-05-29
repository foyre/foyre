"""Data-layer tests for the Validation Pipelines feature (Chunk 1).

Scope: tables get created by `Base.metadata.create_all`, repositories
round-trip rows correctly, FK relationships work, the
default-pipeline-uniqueness helper behaves like its host_clusters peer,
and the single-row policy config repository tolerates the empty case
(falling back to model defaults).

Higher-level concerns (YAML parsing, runner, approval gate, API) are
covered by later chunks.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.domain.enums import (
    ApprovalImpact,
    FailurePolicy,
    HistoryEventType,
    ValidationRunStatus,
    ValidationSeverity,
    ValidationStepStatus,
)
from app.models.request import IntakeRequest
from app.models.user import User
from app.models.validation_artifact import ValidationArtifact
from app.models.validation_pipeline import ValidationPipeline
from app.models.validation_policy_config import ValidationPolicyConfig
from app.models.validation_run import ValidationRun
from app.models.validation_step_result import ValidationStepResult
from app.repositories import (
    validation_artifacts as artifacts_repo,
    validation_pipelines as pipelines_repo,
    validation_policy_configs as policy_repo,
    validation_runs as runs_repo,
    validation_step_results as steps_repo,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Session:
    """In-memory SQLite with a single shared connection (StaticPool) so
    multiple sessions in the same test see the same tables/data."""
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


def _make_user(db: Session, username: str = "admin") -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash="x",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_request(db: Session, user: User) -> IntakeRequest:
    req = IntakeRequest(created_by_id=user.id, status="draft", payload={})
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def _make_pipeline(
    db: Session, user: User, name: str = "default-ai-workload-validation"
) -> ValidationPipeline:
    pipe = ValidationPipeline(
        name=name,
        display_name="Default AI Workload Validation",
        description="seed",
        enabled=True,
        is_default=False,
        version=1,
        default_failure_policy=FailurePolicy.warn.value,
        definition_yaml="apiVersion: foyre.ai/v1alpha1\nkind: ValidationPipeline\n",
        definition_json={"apiVersion": "foyre.ai/v1alpha1", "kind": "ValidationPipeline"},
        created_by_id=user.id,
    )
    return pipelines_repo.save(db, pipe)


# ---------------------------------------------------------------------------
# Tables come up cleanly + new history event types are usable
# ---------------------------------------------------------------------------


def test_create_all_includes_new_tables(db: Session) -> None:
    """Smoke check: every new model can be inserted/queried without
    triggering missing-table errors."""
    user = _make_user(db)
    req = _make_request(db, user)
    pipe = _make_pipeline(db, user)
    run = ValidationRun(
        request_id=req.id,
        pipeline_id=pipe.id,
        pipeline_name=pipe.name,
        pipeline_version=pipe.version,
        pipeline_definition_json=pipe.definition_json,
        status=ValidationRunStatus.queued.value,
        approval_impact=ApprovalImpact.none.value,
        started_by_id=user.id,
    )
    runs_repo.save(db, run)

    step = ValidationStepResult(
        validation_run_id=run.id,
        step_name="workload-inventory",
        step_type="builtin.workload_inventory",
        sort_order=0,
        status=ValidationStepStatus.passed.value,
        severity=ValidationSeverity.none.value,
        required=True,
        failure_policy=FailurePolicy.warn.value,
        summary="all good",
    )
    steps_repo.save(db, step)

    art = ValidationArtifact(
        validation_run_id=run.id,
        step_result_id=step.id,
        artifact_name="inventory.json",
        artifact_type="json",
        content_type="application/json",
        content=b'{"images": []}',
        size_bytes=14,
    )
    artifacts_repo.save(db, art)

    assert runs_repo.get(db, run.id) is not None
    assert steps_repo.get(db, step.id) is not None
    assert artifacts_repo.get(db, art.id) is not None


def test_new_history_event_types_present() -> None:
    """The brief calls out specific event names; assert they exist as
    enum members so accidental renames are caught at test time."""
    expected = {
        "validation_run_started",
        "validation_run_completed",
        "validation_run_failed",
        "validation_approval_blocked",
        "validation_override_used",
        "validation_artifact_created",
    }
    members = {m.value for m in HistoryEventType}
    assert expected <= members


# ---------------------------------------------------------------------------
# Pipeline repository
# ---------------------------------------------------------------------------


def test_pipeline_name_uniqueness(db: Session) -> None:
    user = _make_user(db)
    _make_pipeline(db, user, name="dup")
    with pytest.raises(Exception):  # noqa: BLE001 -- IntegrityError variant
        # Same name should be rejected by the unique index.
        _make_pipeline(db, user, name="dup")


def test_pipeline_lookup_by_name_and_default(db: Session) -> None:
    user = _make_user(db)
    a = _make_pipeline(db, user, name="alpha")
    b = _make_pipeline(db, user, name="beta")
    b.is_default = True
    pipelines_repo.save(db, b)

    assert pipelines_repo.get_by_name(db, "alpha").id == a.id
    assert pipelines_repo.get_by_name(db, "beta").id == b.id
    assert pipelines_repo.get_default(db).id == b.id


def test_clear_other_defaults_idempotent(db: Session) -> None:
    """Mirrors the host_clusters helper: only one pipeline may be the
    default at a time."""
    user = _make_user(db)
    a = _make_pipeline(db, user, name="alpha")
    b = _make_pipeline(db, user, name="beta")
    a.is_default = True
    b.is_default = True
    pipelines_repo.save(db, a)
    pipelines_repo.save(db, b)

    pipelines_repo.clear_other_defaults(db, keep_id=b.id)
    db.refresh(a)
    db.refresh(b)
    assert a.is_default is False
    assert b.is_default is True


def test_list_enabled_excludes_disabled(db: Session) -> None:
    user = _make_user(db)
    a = _make_pipeline(db, user, name="alpha")
    b = _make_pipeline(db, user, name="beta")
    a.enabled = False
    pipelines_repo.save(db, a)

    enabled = pipelines_repo.list_enabled(db)
    assert {p.name for p in enabled} == {b.name}


# ---------------------------------------------------------------------------
# Run + step + artifact relationships
# ---------------------------------------------------------------------------


def test_run_lookups_by_request(db: Session) -> None:
    user = _make_user(db)
    req = _make_request(db, user)
    pipe = _make_pipeline(db, user)

    run1 = runs_repo.save(
        db,
        ValidationRun(
            request_id=req.id,
            pipeline_id=pipe.id,
            pipeline_name=pipe.name,
            pipeline_version=pipe.version,
            pipeline_definition_json=pipe.definition_json,
            status=ValidationRunStatus.passed.value,
        ),
    )
    run2 = runs_repo.save(
        db,
        ValidationRun(
            request_id=req.id,
            pipeline_id=pipe.id,
            pipeline_name=pipe.name,
            pipeline_version=pipe.version,
            pipeline_definition_json=pipe.definition_json,
            status=ValidationRunStatus.queued.value,
        ),
    )

    listed = runs_repo.list_for_request(db, req.id)
    # Newest first.
    assert [r.id for r in listed] == [run2.id, run1.id]
    assert runs_repo.latest_for_request(db, req.id).id == run2.id


def test_step_result_lookup_by_step_name(db: Session) -> None:
    user = _make_user(db)
    req = _make_request(db, user)
    pipe = _make_pipeline(db, user)
    run = runs_repo.save(
        db,
        ValidationRun(
            request_id=req.id,
            pipeline_id=pipe.id,
            pipeline_name=pipe.name,
            pipeline_version=pipe.version,
            pipeline_definition_json=pipe.definition_json,
        ),
    )
    steps_repo.save(
        db,
        ValidationStepResult(
            validation_run_id=run.id,
            step_name="workload-inventory",
            step_type="builtin.workload_inventory",
            sort_order=0,
        ),
    )
    found = steps_repo.get_by_step_name(db, run.id, "workload-inventory")
    assert found is not None
    assert found.step_type == "builtin.workload_inventory"
    assert steps_repo.get_by_step_name(db, run.id, "missing") is None


def test_cascade_delete_run_cleans_steps_and_artifacts(db: Session) -> None:
    user = _make_user(db)
    req = _make_request(db, user)
    pipe = _make_pipeline(db, user)
    run = runs_repo.save(
        db,
        ValidationRun(
            request_id=req.id,
            pipeline_id=pipe.id,
            pipeline_name=pipe.name,
            pipeline_version=pipe.version,
            pipeline_definition_json=pipe.definition_json,
        ),
    )
    step = steps_repo.save(
        db,
        ValidationStepResult(
            validation_run_id=run.id,
            step_name="x",
            step_type="builtin.workload_inventory",
        ),
    )
    art = artifacts_repo.save(
        db,
        ValidationArtifact(
            validation_run_id=run.id,
            step_result_id=step.id,
            artifact_name="x.json",
            artifact_type="json",
            content_type="application/json",
            content=b"{}",
            size_bytes=2,
        ),
    )

    db.delete(run)
    db.commit()

    assert steps_repo.get(db, step.id) is None
    assert artifacts_repo.get(db, art.id) is None


def test_artifact_read_bytes_indirection(db: Session) -> None:
    """The repository's `read_bytes()` is the seam that lets us swap to
    a filesystem-backed tier later. Today it returns `row.content`."""
    user = _make_user(db)
    req = _make_request(db, user)
    pipe = _make_pipeline(db, user)
    run = runs_repo.save(
        db,
        ValidationRun(
            request_id=req.id,
            pipeline_id=pipe.id,
            pipeline_name=pipe.name,
            pipeline_version=pipe.version,
            pipeline_definition_json=pipe.definition_json,
        ),
    )
    art = artifacts_repo.save(
        db,
        ValidationArtifact(
            validation_run_id=run.id,
            artifact_name="raw.txt",
            artifact_type="text",
            content_type="text/plain",
            content=b"hello",
            size_bytes=5,
        ),
    )
    assert artifacts_repo.read_bytes(art) == b"hello"


# ---------------------------------------------------------------------------
# Policy config (single row, defaults)
# ---------------------------------------------------------------------------


def test_policy_config_empty_returns_none_so_callers_can_use_defaults(db: Session) -> None:
    assert policy_repo.get(db) is None


def test_policy_config_persists_overrides(db: Session) -> None:
    user = _make_user(db)
    row = ValidationPolicyConfig(
        require_validation_before_approval=True,
        block_approval_on_failed_validation=True,
        allow_validation_override=False,
        updated_by_id=user.id,
    )
    policy_repo.save(db, row)

    fetched = policy_repo.get(db)
    assert fetched is not None
    assert fetched.require_validation_before_approval is True
    assert fetched.allow_validation_override is False


def test_policy_config_default_values_match_brief() -> None:
    """In-memory instance (no DB) must reflect the defaults the approval
    gate falls back to when no row exists."""
    row = ValidationPolicyConfig()
    # SQLAlchemy populates Python-side defaults at flush time, not
    # construction; assert the column defaults declared on the model.
    col_defaults = {
        c.name: c.default.arg if c.default is not None else None
        for c in ValidationPolicyConfig.__table__.columns
    }
    assert col_defaults["require_validation_before_approval"] is False
    assert col_defaults["block_approval_on_failed_validation"] is True
    assert col_defaults["allow_validation_override"] is True
    assert row is not None  # silence unused-var linter
