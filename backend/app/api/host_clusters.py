"""Admin endpoints for managing host Kubernetes cluster configurations."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_role
from app.domain.enums import Role
from app.models.host_cluster_config import HostClusterConfig
from app.models.user import User
from app.provisioning import crypto
from app.provisioning.kube_client import test_connection as kube_test
from app.repositories import host_clusters as repo
from app.schemas.host_cluster import (
    HostClusterCreate,
    HostClusterOut,
    HostClusterUpdate,
    TestConnectionRequest,
    TestConnectionResult,
)

router = APIRouter()


def _ensure_encryption() -> None:
    if not crypto.is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "APP_SECRET_KEY is not configured. See backend/.env.example for instructions.",
        )


def _apply_test_result(row: HostClusterConfig, result) -> None:
    row.last_tested_at = datetime.now(tz=timezone.utc)
    if result.success:
        row.last_test_status = "connected"
        row.last_test_error = None
        row.last_test_cluster_version = result.cluster_version
        row.last_test_node_count = result.node_count
        row.last_test_has_storage_class = result.has_storage_class
    else:
        row.last_test_status = "failed"
        row.last_test_error = result.error
        row.last_test_cluster_version = None
        row.last_test_node_count = None
        row.last_test_has_storage_class = None


@router.get("", response_model=list[HostClusterOut])
def list_host_clusters(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    return repo.list_all(db)


@router.post("", response_model=HostClusterOut, status_code=201)
def create_host_cluster(
    body: HostClusterCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    _ensure_encryption()
    if repo.get_by_name(db, body.name):
        raise HTTPException(status.HTTP_409_CONFLICT, f"name '{body.name}' already exists")

    row = HostClusterConfig(
        name=body.name,
        provider=body.provider,
        kubeconfig_encrypted=crypto.encrypt(body.kubeconfig),
        context_name=body.context_name,
        external_node_host=body.external_node_host,
        is_default=body.is_default,
        is_enabled=body.is_enabled,
        ttl_hours=body.defaults.ttl_hours,
        cpu_quota=body.defaults.cpu_quota,
        memory_quota=body.defaults.memory_quota,
        storage_quota=body.defaults.storage_quota,
        apply_default_network_policy=body.defaults.apply_default_network_policy,
        apply_default_resource_quota=body.defaults.apply_default_resource_quota,
        allow_regenerate_kubeconfig=body.defaults.allow_regenerate_kubeconfig,
    )
    # Test connectivity immediately so the UI gets a meaningful last_test_*.
    result = kube_test(body.kubeconfig, body.context_name)
    _apply_test_result(row, result)

    row = repo.save(db, row)
    if row.is_default:
        repo.clear_other_defaults(db, keep_id=row.id)
    return row


@router.get("/{host_id}", response_model=HostClusterOut)
def get_host_cluster(
    host_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    row = repo.get(db, host_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    return row


@router.patch("/{host_id}", response_model=HostClusterOut)
def update_host_cluster(
    host_id: int,
    body: HostClusterUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    row = repo.get(db, host_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    if body.name is not None and body.name != row.name:
        if repo.get_by_name(db, body.name):
            raise HTTPException(status.HTTP_409_CONFLICT, f"name '{body.name}' already exists")
        row.name = body.name
    if body.provider is not None:
        row.provider = body.provider
    if body.kubeconfig is not None:
        if not body.kubeconfig.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "kubeconfig cannot be empty; omit the field to leave it unchanged",
            )
        _ensure_encryption()
        row.kubeconfig_encrypted = crypto.encrypt(body.kubeconfig)
        # Re-test immediately whenever kubeconfig changes.
        result = kube_test(body.kubeconfig, body.context_name or row.context_name)
        _apply_test_result(row, result)
    if body.context_name is not None:
        row.context_name = body.context_name or None
    if body.external_node_host is not None:
        row.external_node_host = body.external_node_host or None
    if body.is_default is not None:
        row.is_default = body.is_default
    if body.is_enabled is not None:
        row.is_enabled = body.is_enabled
    if body.defaults is not None:
        row.ttl_hours = body.defaults.ttl_hours
        row.cpu_quota = body.defaults.cpu_quota
        row.memory_quota = body.defaults.memory_quota
        row.storage_quota = body.defaults.storage_quota
        row.apply_default_network_policy = body.defaults.apply_default_network_policy
        row.apply_default_resource_quota = body.defaults.apply_default_resource_quota
        row.allow_regenerate_kubeconfig = body.defaults.allow_regenerate_kubeconfig

    row = repo.save(db, row)
    if row.is_default:
        repo.clear_other_defaults(db, keep_id=row.id)
    return row


@router.delete("/{host_id}", status_code=204)
def delete_host_cluster(
    host_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    row = repo.get(db, host_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    repo.delete(db, row)


@router.post("/test-connection", response_model=TestConnectionResult)
def test_unsaved_connection(
    body: TestConnectionRequest,
    _: User = Depends(require_role(Role.admin)),
):
    """Test a freshly-pasted kubeconfig before saving it."""
    result = kube_test(body.kubeconfig, body.context_name)
    return TestConnectionResult(
        success=result.success,
        cluster_version=result.cluster_version,
        node_count=result.node_count,
        has_storage_class=result.has_storage_class,
        can_create_namespaces=result.can_create_namespaces,
        can_create_rbac=result.can_create_rbac,
        error=result.error,
    )


@router.post("/{host_id}/test-connection", response_model=HostClusterOut)
def test_saved_connection(
    host_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.admin)),
):
    """Re-test a saved host cluster. Updates last_test_* on the row."""
    _ensure_encryption()
    row = repo.get(db, host_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    kubeconfig_yaml = crypto.decrypt(row.kubeconfig_encrypted)
    result = kube_test(kubeconfig_yaml, row.context_name)
    _apply_test_result(row, result)
    return repo.save(db, row)
