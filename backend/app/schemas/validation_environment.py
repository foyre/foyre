"""DTOs for validation environments.

The user kubeconfig is *only* exposed through the dedicated /kubeconfig
endpoint — never in list or detail responses.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import ValidationEnvStatus


class ValidationEnvCreate(BaseModel):
    """Empty body for now — host cluster is picked from the default, and the
    namespace + name are derived from the request id.
    """

    pass


class ValidationEnvOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    host_cluster_config_id: int
    status: ValidationEnvStatus
    namespace: str
    vcluster_name: str
    provider: str
    external_endpoint: str | None
    expires_at: datetime | None
    extensions_used: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    torn_down_at: datetime | None


class KubeconfigOut(BaseModel):
    """Raw YAML returned once so the requester can download it."""

    kubeconfig: str
