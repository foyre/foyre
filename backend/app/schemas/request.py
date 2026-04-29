"""DTOs for intake requests.

`IntakePayload` is the typed shape of the form answers. Keep this as the one
place where field-level validation lives. When a field is added to the form
schema, add it here too.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    DataClassification,
    Environment,
    RequestStatus,
    RiskLevel,
    WorkloadType,
    YesNoUnknown,
)
from app.schemas.user import UserRef


class IntakePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_name: str = Field(min_length=1, max_length=200)
    business_owner: str
    technical_owner: str
    team: str
    description: str
    environment: Environment

    workload_type: WorkloadType

    handles_sensitive_data: YesNoUnknown
    data_classification: DataClassification
    uses_enterprise_documents: bool = False
    uses_vector_db: bool = False
    vector_db_name: str | None = None
    calls_external_model_api: bool = False
    uses_internal_models: bool = False
    takes_actions: bool = False
    internet_egress: bool = False
    gpu_required: bool = False

    justification: str | None = None
    timeline: str | None = None
    architecture_notes: str | None = None


class RequestCreate(BaseModel):
    """On create, the requester may submit a partial payload (draft)."""

    payload: dict


class RequestUpdate(BaseModel):
    payload: dict


class StatusChange(BaseModel):
    new_status: RequestStatus


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_id: int
    created_by: UserRef | None = None
    status: RequestStatus
    payload: dict
    risk_level: RiskLevel | None
    risk_reasons: list[str] | None
    created_at: datetime
    updated_at: datetime
