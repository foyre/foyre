"""DTOs for host cluster config.

Crucial invariant: the kubeconfig itself is *never* included in a response.
`kubeconfig` is a write-only field on creates/updates. GETs return `*Out` only.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HostClusterDefaults(BaseModel):
    """Defaults applied to newly-created validation clusters."""

    ttl_hours: int = Field(default=72, ge=1, le=24 * 30)
    cpu_quota: str = Field(default="4")
    memory_quota: str = Field(default="8Gi")
    storage_quota: str = Field(default="10Gi")
    apply_default_network_policy: bool = True
    apply_default_resource_quota: bool = True
    allow_regenerate_kubeconfig: bool = True


class HostClusterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(default="vcluster")
    kubeconfig: str = Field(min_length=1)
    context_name: str | None = None
    external_node_host: str | None = None
    is_default: bool = False
    is_enabled: bool = True
    defaults: HostClusterDefaults = HostClusterDefaults()


class HostClusterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    provider: str | None = None
    # Absent = keep existing encrypted kubeconfig. Empty string is rejected.
    kubeconfig: str | None = None
    context_name: str | None = None
    external_node_host: str | None = None
    is_default: bool | None = None
    is_enabled: bool | None = None
    defaults: HostClusterDefaults | None = None


class HostClusterOut(BaseModel):
    """Never carries the kubeconfig. Returned from all GETs."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider: str
    context_name: str | None
    external_node_host: str | None
    is_default: bool
    is_enabled: bool

    ttl_hours: int
    cpu_quota: str
    memory_quota: str
    storage_quota: str
    apply_default_network_policy: bool
    apply_default_resource_quota: bool
    allow_regenerate_kubeconfig: bool

    last_tested_at: datetime | None
    last_test_status: str
    last_test_error: str | None
    last_test_cluster_version: str | None
    last_test_node_count: int | None
    last_test_has_storage_class: bool | None

    created_at: datetime
    updated_at: datetime


class TestConnectionRequest(BaseModel):
    """Test an unsaved kubeconfig. Either provide a raw kubeconfig string, or
    reference an already-saved host by id (via the `/{id}/test-connection` route).
    """

    kubeconfig: str = Field(min_length=1)
    context_name: str | None = None


class TestConnectionResult(BaseModel):
    success: bool
    # When success=True:
    cluster_version: str | None = None
    node_count: int | None = None
    has_storage_class: bool | None = None
    can_create_namespaces: bool | None = None
    can_create_rbac: bool | None = None
    # When success=False:
    error: str | None = None
