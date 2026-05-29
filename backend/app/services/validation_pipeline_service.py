"""Validation pipeline definitions: parse, validate, persist.

This is the single source of truth for "is this pipeline definition
valid, and what is its normalized form?" Admins author pipelines as YAML;
this module parses + normalizes them into the JSON the runner (chunk 3+)
consumes, and enforces structural invariants so a saved pipeline is
always runnable.

Invariants enforced on parse:
  - Top-level `apiVersion`/`kind` match the supported schema.
  - `metadata.name` is a valid slug.
  - `spec.steps` is a non-empty list.
  - Every step has a unique, slug-shaped `name` and a `type` that exists
    in the step-type registry (`app.domain.validation_steps`).
  - `dependsOn` references only existing steps, with no self-dependency
    and no dependency cycles.
  - `failurePolicy` (step or pipeline default) is one of ignore/warn/block.
  - `timeoutSeconds` is within sane bounds.
  - `custom.kubernetes_job` steps declare a container `image`.

Persistence mirrors the host-cluster + form-schema conventions:
routes → this service (orchestration + HTTPException) → repository (CRUD).
Default-pipeline uniqueness is enforced here (one default at a time).
"""
from __future__ import annotations

import re
from typing import Any

import yaml
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import FailurePolicy
from app.domain.validation_steps import (
    PLANNED_STEP_TYPES,
    SUPPORTED_STEP_TYPES,
)
from app.models.user import User
from app.models.validation_pipeline import ValidationPipeline
from app.repositories import validation_pipelines as repo

SUPPORTED_API_VERSION = "foyre.ai/v1alpha1"
SUPPORTED_KIND = "ValidationPipeline"

# Step + pipeline names are Kubernetes-ish slugs (lowercase, digits,
# hyphens). Distinct from form-field names (underscores) on purpose:
# pipeline/step names tend to map to k8s object names.
_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")

_VALID_FAILURE_POLICIES = {p.value for p in FailurePolicy}

# Bounds for per-step timeout. Upper bound keeps a runaway custom job from
# pinning the runner thread indefinitely; image scans can be slow, hence 1h.
_MIN_TIMEOUT_SECONDS = 1
_MAX_TIMEOUT_SECONDS = 3600
_DEFAULT_TIMEOUT_SECONDS = 300


def _bad(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, msg)


# ---------------------------------------------------------------------------
# Parse + validate
# ---------------------------------------------------------------------------


def parse_yaml(raw: str) -> dict[str, Any]:
    """Parse a YAML document into a dict, raising 400 on syntax errors."""
    if not isinstance(raw, str) or not raw.strip():
        raise _bad("Pipeline definition is empty.")
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise _bad(f"Invalid YAML: {e}")
    if not isinstance(loaded, dict):
        raise _bad("Pipeline definition must be a YAML mapping.")
    return loaded


def _normalize_failure_policy(value: Any, *, where: str, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or value not in _VALID_FAILURE_POLICIES:
        raise _bad(
            f"{where}: failurePolicy must be one of "
            f"{sorted(_VALID_FAILURE_POLICIES)} (got {value!r})."
        )
    return value


def _normalize_timeout(value: Any, *, where: str) -> int:
    if value is None:
        return _DEFAULT_TIMEOUT_SECONDS
    if isinstance(value, bool) or not isinstance(value, int):
        raise _bad(f"{where}: timeoutSeconds must be an integer.")
    if not (_MIN_TIMEOUT_SECONDS <= value <= _MAX_TIMEOUT_SECONDS):
        raise _bad(
            f"{where}: timeoutSeconds must be between {_MIN_TIMEOUT_SECONDS} "
            f"and {_MAX_TIMEOUT_SECONDS} (got {value})."
        )
    return value


def _unknown_type_message(step_type: str) -> str:
    if step_type in PLANNED_STEP_TYPES:
        return (
            f"Step type '{step_type}' is planned but not yet available in "
            "this version of Foyre."
        )
    return (
        f"Unknown step type '{step_type}'. Supported types: "
        f"{sorted(SUPPORTED_STEP_TYPES)}."
    )


def _normalize_step(raw_step: Any, *, index: int, pipeline_default_policy: str) -> dict[str, Any]:
    where = f"step #{index + 1}"
    if not isinstance(raw_step, dict):
        raise _bad(f"{where}: each step must be a mapping.")

    name = raw_step.get("name")
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise _bad(
            f"{where}: name is required and must be a slug matching "
            r"^[a-z][a-z0-9-]{0,62}$ "
            f"(got {name!r})."
        )
    where = f"step '{name}'"

    step_type = raw_step.get("type")
    if not isinstance(step_type, str):
        raise _bad(f"{where}: type is required.")
    if step_type not in SUPPORTED_STEP_TYPES:
        raise _bad(f"{where}: {_unknown_type_message(step_type)}")

    depends_on = raw_step.get("dependsOn") or []
    if not isinstance(depends_on, list) or not all(isinstance(d, str) for d in depends_on):
        raise _bad(f"{where}: dependsOn must be a list of step names.")

    config = raw_step.get("config")
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise _bad(f"{where}: config must be a mapping.")

    spec = SUPPORTED_STEP_TYPES[step_type]

    # Lightweight type-specific guardrail. Deeper validation (privileged
    # spec rejection, etc.) for custom jobs lands in chunk 4.
    if spec.custom_job:
        image = config.get("image")
        if not isinstance(image, str) or not image.strip():
            raise _bad(
                f"{where}: custom.kubernetes_job requires a non-empty "
                "config.image."
            )

    display_name = raw_step.get("displayName")
    if display_name is not None and not isinstance(display_name, str):
        raise _bad(f"{where}: displayName must be a string.")

    description = raw_step.get("description")
    if description is not None and not isinstance(description, str):
        raise _bad(f"{where}: description must be a string.")

    enabled = raw_step.get("enabled", True)
    if not isinstance(enabled, bool):
        raise _bad(f"{where}: enabled must be a boolean.")

    required = raw_step.get("required", False)
    if not isinstance(required, bool):
        raise _bad(f"{where}: required must be a boolean.")

    return {
        "name": name,
        "type": step_type,
        "displayName": display_name or spec.display_name,
        "description": description,
        "enabled": enabled,
        "required": required,
        "dependsOn": depends_on,
        "timeoutSeconds": _normalize_timeout(raw_step.get("timeoutSeconds"), where=where),
        "failurePolicy": _normalize_failure_policy(
            raw_step.get("failurePolicy"), where=where, default=pipeline_default_policy
        ),
        "config": config,
    }


def _assert_no_dependency_cycles(steps: list[dict[str, Any]]) -> None:
    """Kahn's algorithm; raises 400 if a cycle or missing dep is found."""
    names = {s["name"] for s in steps}
    deps: dict[str, set[str]] = {}
    for s in steps:
        for d in s["dependsOn"]:
            if d == s["name"]:
                raise _bad(f"step '{s['name']}': cannot depend on itself.")
            if d not in names:
                raise _bad(
                    f"step '{s['name']}': dependsOn references unknown step "
                    f"'{d}'."
                )
        deps[s["name"]] = set(s["dependsOn"])

    # Kahn topological sort.
    no_incoming = [n for n in names if not deps[n]]
    resolved: list[str] = []
    deps_work = {n: set(d) for n, d in deps.items()}
    while no_incoming:
        n = no_incoming.pop()
        resolved.append(n)
        for other, other_deps in deps_work.items():
            if n in other_deps:
                other_deps.discard(n)
                if not other_deps and other not in resolved and other not in no_incoming:
                    no_incoming.append(other)
    if len(resolved) != len(names):
        unresolved = sorted(names - set(resolved))
        raise _bad(
            "Pipeline has a dependency cycle involving steps: "
            f"{unresolved}."
        )


def parse_and_validate(raw: str | dict[str, Any]) -> dict[str, Any]:
    """Validate a pipeline definition and return its normalized JSON form.

    Accepts either a YAML string (the user-facing format) or an
    already-parsed dict (used internally / for JSON callers).
    """
    doc = parse_yaml(raw) if isinstance(raw, str) else raw
    if not isinstance(doc, dict):
        raise _bad("Pipeline definition must be a mapping.")

    api_version = doc.get("apiVersion")
    if api_version != SUPPORTED_API_VERSION:
        raise _bad(
            f"Unsupported apiVersion {api_version!r}; expected "
            f"{SUPPORTED_API_VERSION!r}."
        )
    if doc.get("kind") != SUPPORTED_KIND:
        raise _bad(
            f"Unsupported kind {doc.get('kind')!r}; expected {SUPPORTED_KIND!r}."
        )

    metadata = doc.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise _bad("metadata must be a mapping.")
    name = metadata.get("name")
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise _bad(
            "metadata.name is required and must be a slug matching "
            r"^[a-z][a-z0-9-]{0,62}$."
        )
    display_name = metadata.get("displayName")
    if display_name is not None and not isinstance(display_name, str):
        raise _bad("metadata.displayName must be a string.")
    description = metadata.get("description")
    if description is not None and not isinstance(description, str):
        raise _bad("metadata.description must be a string.")

    spec = doc.get("spec") or {}
    if not isinstance(spec, dict):
        raise _bad("spec must be a mapping.")

    pipeline_default_policy = _normalize_failure_policy(
        spec.get("failurePolicy"), where="spec", default=FailurePolicy.warn.value
    )

    raw_steps = spec.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise _bad("spec.steps must be a non-empty list.")

    steps: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for i, raw_step in enumerate(raw_steps):
        step = _normalize_step(
            raw_step, index=i, pipeline_default_policy=pipeline_default_policy
        )
        if step["name"] in seen_names:
            raise _bad(f"Duplicate step name '{step['name']}'.")
        seen_names.add(step["name"])
        steps.append(step)

    _assert_no_dependency_cycles(steps)

    return {
        "apiVersion": SUPPORTED_API_VERSION,
        "kind": SUPPORTED_KIND,
        "name": name,
        "displayName": display_name or name,
        "description": description,
        "failurePolicy": pipeline_default_policy,
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def list_pipelines(db: Session) -> list[ValidationPipeline]:
    return repo.list_all(db)


def get_pipeline(db: Session, pipeline_id: int) -> ValidationPipeline:
    row = repo.get(db, pipeline_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "pipeline not found")
    return row


def create_pipeline(
    db: Session, user: User, definition_yaml: str, *, enabled: bool = True, is_default: bool = False
) -> ValidationPipeline:
    normalized = parse_and_validate(definition_yaml)
    name = normalized["name"]
    if repo.get_by_name(db, name):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"a pipeline named '{name}' already exists",
        )
    row = ValidationPipeline(
        name=name,
        display_name=normalized["displayName"],
        description=normalized.get("description"),
        enabled=enabled,
        is_default=is_default,
        version=1,
        default_failure_policy=normalized["failurePolicy"],
        definition_yaml=definition_yaml,
        definition_json=normalized,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    row = repo.save(db, row)
    if row.is_default:
        repo.clear_other_defaults(db, keep_id=row.id)
    return row


def update_pipeline(
    db: Session,
    user: User,
    pipeline_id: int,
    *,
    definition_yaml: str | None = None,
    enabled: bool | None = None,
) -> ValidationPipeline:
    row = get_pipeline(db, pipeline_id)

    if definition_yaml is not None:
        normalized = parse_and_validate(definition_yaml)
        new_name = normalized["name"]
        # Renaming to collide with another pipeline is rejected.
        existing = repo.get_by_name(db, new_name)
        if existing and existing.id != row.id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"a pipeline named '{new_name}' already exists",
            )
        row.name = new_name
        row.display_name = normalized["displayName"]
        row.description = normalized.get("description")
        row.default_failure_policy = normalized["failurePolicy"]
        row.definition_yaml = definition_yaml
        row.definition_json = normalized
        row.version = (row.version or 1) + 1

    if enabled is not None:
        row.enabled = enabled

    row.updated_by_id = user.id
    return repo.save(db, row)


def delete_pipeline(db: Session, pipeline_id: int) -> None:
    row = get_pipeline(db, pipeline_id)
    repo.delete(db, row)


def set_default(db: Session, pipeline_id: int) -> ValidationPipeline:
    row = get_pipeline(db, pipeline_id)
    if not row.enabled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "cannot set a disabled pipeline as the default",
        )
    row.is_default = True
    row = repo.save(db, row)
    repo.clear_other_defaults(db, keep_id=row.id)
    return row


def resolve_for_run(db: Session, pipeline_id: int | None) -> ValidationPipeline:
    """Pick the pipeline to run: explicit id, else the default.

    Used by the run endpoint (chunk 3). Centralized here so the
    "which pipeline?" logic lives with the rest of pipeline management.
    """
    if pipeline_id is not None:
        row = get_pipeline(db, pipeline_id)
    else:
        row = repo.get_default(db)
        if not row:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "no pipeline_id provided and no default pipeline is configured",
            )
    if not row.enabled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"pipeline '{row.name}' is disabled",
        )
    return row
