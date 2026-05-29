"""Canonical enums shared by models, services, and the API.

Single source of truth. The frontend receives these via `/api/meta/form-schema`
rather than duplicating them.
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    requester = "requester"
    reviewer = "reviewer"
    architect = "architect"
    admin = "admin"


# Roles that can view all requests, update status, and post comments.
# Centralized so services and route guards stay in sync.
PRIVILEGED_ROLES: frozenset[Role] = frozenset(
    {Role.reviewer, Role.architect, Role.admin}
)


class RequestStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    # Requester has deployed into their validation environment and is asking
    # a reviewer to take a look. Reviewers can act on this status the same way
    # they act on `submitted`.
    ready_for_review = "ready_for_review"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    unknown = "unknown"


class WorkloadType(str, Enum):
    chatbot = "chatbot"
    rag = "rag"
    inference_api = "inference_api"
    agent = "agent"
    training = "training"
    other = "other"


class Environment(str, Enum):
    dev = "dev"
    validation = "validation"
    prod = "prod"


class DataClassification(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    regulated = "regulated"


class YesNoUnknown(str, Enum):
    yes = "yes"
    no = "no"
    unknown = "unknown"


class HistoryEventType(str, Enum):
    created = "created"
    updated = "updated"
    submitted = "submitted"
    status_changed = "status_changed"
    commented = "commented"
    risk_evaluated = "risk_evaluated"
    validation_env_requested = "validation_env_requested"
    validation_env_ready = "validation_env_ready"
    validation_env_failed = "validation_env_failed"
    validation_env_torn_down = "validation_env_torn_down"
    # Validation Pipelines (request-scoped events only — pipeline-level
    # admin actions like create/update aren't tied to a single request and
    # are intentionally not recorded here.)
    validation_run_started = "validation_run_started"
    validation_run_completed = "validation_run_completed"
    validation_run_failed = "validation_run_failed"
    validation_approval_blocked = "validation_approval_blocked"
    validation_override_used = "validation_override_used"
    validation_artifact_created = "validation_artifact_created"


class ValidationEnvStatus(str, Enum):
    provisioning = "provisioning"
    ready = "ready"
    failed = "failed"
    torn_down = "torn_down"


# ---------------------------------------------------------------------------
# Validation Pipelines
# ---------------------------------------------------------------------------


class ValidationRunStatus(str, Enum):
    """Lifecycle of one ValidationRun.

    - `queued`   : created, not yet started by the runner thread.
    - `running`  : at least one step has begun executing.
    - `passed`   : all required steps passed.
    - `warning`  : at least one step ended with status=warning, no blocking
                   step failed.
    - `failed`   : at least one required step ended with status=failed.
    - `error`    : the runner itself errored before finishing (infra fault,
                   not a step result).
    - `cancelled`: marked cancelled by an operator (best-effort; threads
                   can't be safely interrupted in Python — see the runner
                   for the exact semantics).
    """

    queued = "queued"
    running = "running"
    passed = "passed"
    warning = "warning"
    failed = "failed"
    error = "error"
    cancelled = "cancelled"


class ValidationStepStatus(str, Enum):
    queued = "queued"
    running = "running"
    passed = "passed"
    warning = "warning"
    failed = "failed"
    error = "error"
    skipped = "skipped"


class ValidationSeverity(str, Enum):
    """Severity assigned to a step result or an individual finding."""

    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FailurePolicy(str, Enum):
    """How a step's failure rolls up into the run + approval impact.

    - `ignore`: never affects the run status or approval impact.
    - `warn`  : a failure shows the step as warning; run is at most warning.
    - `block` : a failure marks the run failed and contributes to a
                `blocked` approval impact.
    """

    ignore = "ignore"
    warn = "warn"
    block = "block"


class ApprovalImpact(str, Enum):
    """Worst-case approval impact derived from a run's step results.

    Approved-then-overridden requests still record `blocked` here; the
    history event records the override + reason separately.
    """

    none = "none"
    warning = "warning"
    blocked = "blocked"
