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


class ValidationEnvStatus(str, Enum):
    provisioning = "provisioning"
    ready = "ready"
    failed = "failed"
    torn_down = "torn_down"
