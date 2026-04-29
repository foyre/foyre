"""High-level provisioning orchestration.

Wraps the vcluster provider, runs long-running work in a background thread,
persists status transitions on the ValidationEnvironment row, and records
history events on the request.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.domain.enums import HistoryEventType, ValidationEnvStatus
from app.models.host_cluster_config import HostClusterConfig
from app.models.validation_environment import ValidationEnvironment
from app.provisioning import crypto
from app.provisioning.providers import vcluster
from app.repositories import host_clusters as host_repo
from app.repositories import validation_environments as env_repo
from app.services import history_service

log = logging.getLogger(__name__)


class ProvisioningUnavailable(RuntimeError):
    """Raised when no usable host cluster is configured."""


def _pick_host_cluster(db: Session) -> HostClusterConfig:
    hosts = host_repo.list_all(db)
    enabled = [h for h in hosts if h.is_enabled]
    if not enabled:
        raise ProvisioningUnavailable(
            "No enabled host cluster is configured. Ask an admin to add one in Settings."
        )
    for h in enabled:
        if h.is_default:
            return h
    return enabled[0]


def _derive_names(request_id: int, env_id: int) -> tuple[str, str]:
    """Stable, collision-avoiding namespace + vcluster name for a (request, env)."""
    # Namespace: foyre-req-<request>-<env>
    # vcluster_name: req-<request>-<env>  (k8s-object-safe, short)
    namespace = f"foyre-req-{request_id}-{env_id}"
    vcluster_name = f"req-{request_id}-{env_id}"
    return namespace, vcluster_name


def start_provisioning(
    db: Session, request_id: int
) -> ValidationEnvironment:
    """Create a ValidationEnvironment row in 'provisioning' and kick off a worker thread."""
    host = _pick_host_cluster(db)

    # Create the env row first so we have an id for the namespace/name.
    env = ValidationEnvironment(
        request_id=request_id,
        host_cluster_config_id=host.id,
        status=ValidationEnvStatus.provisioning.value,
        namespace="",
        vcluster_name="",
        provider=host.provider,
    )
    env = env_repo.save(db, env)

    namespace, vcluster_name = _derive_names(request_id, env.id)
    env.namespace = namespace
    env.vcluster_name = vcluster_name
    env.expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=host.ttl_hours)
    env = env_repo.save(db, env)

    # Fire off the actual work. Daemon thread so we don't block shutdown.
    t = threading.Thread(
        target=_provision_in_background,
        args=(env.id, host.id),
        name=f"provision-env-{env.id}",
        daemon=True,
    )
    t.start()
    return env


def _provision_in_background(env_id: int, host_id: int) -> None:
    """Worker entry point. Runs in its own thread with a fresh DB session."""
    db = SessionLocal()
    try:
        env = env_repo.get(db, env_id)
        host = host_repo.get(db, host_id)
        if env is None or host is None:
            log.error("env or host disappeared before provisioning", extra={
                "env_id": env_id, "host_id": host_id})
            return
        try:
            host_kubeconfig_yaml = crypto.decrypt(host.kubeconfig_encrypted)
            result = vcluster.provision(
                host_kubeconfig_yaml=host_kubeconfig_yaml,
                host_context_name=host.context_name,
                namespace=env.namespace,
                vcluster_name=env.vcluster_name,
                external_node_host=host.external_node_host,
            )
            env.status = ValidationEnvStatus.ready.value
            env.external_endpoint = result.external_endpoint
            env.user_kubeconfig_encrypted = crypto.encrypt(result.user_kubeconfig)
            env.last_error = None
            env_repo.save(db, env)
            history_service.record_event(
                db,
                request_id=env.request_id,
                actor_id=_system_actor_id(db, env),
                event_type=HistoryEventType.validation_env_ready,
                detail={
                    "env_id": env.id,
                    "endpoint": result.external_endpoint,
                    "vcluster_name": env.vcluster_name,
                },
            )
        except Exception as e:
            log.exception("provisioning failed for env %s", env_id)
            env = env_repo.get(db, env_id)  # re-fetch in case of race
            if env is None:
                return
            env.status = ValidationEnvStatus.failed.value
            env.last_error = f"{type(e).__name__}: {e}"[:2000]
            env_repo.save(db, env)
            history_service.record_event(
                db,
                request_id=env.request_id,
                actor_id=_system_actor_id(db, env),
                event_type=HistoryEventType.validation_env_failed,
                detail={"env_id": env.id, "error": env.last_error},
            )
    finally:
        db.close()


def _system_actor_id(db: Session, env: ValidationEnvironment) -> int:
    """The actor for provisioning events is the request owner (the person who clicked
    the button). If the row is gone for any reason, fall back to id 1."""
    from app.models.request import IntakeRequest

    req = db.get(IntakeRequest, env.request_id)
    return req.created_by_id if req else 1


def teardown(db: Session, env: ValidationEnvironment, actor_id: int) -> ValidationEnvironment:
    """Synchronously tear down a validation env. Short enough operation to run inline."""
    if env.status == ValidationEnvStatus.torn_down.value:
        return env
    host = host_repo.get(db, env.host_cluster_config_id)
    if host is None:
        # Host is gone — mark torn down without doing anything on the cluster.
        env.status = ValidationEnvStatus.torn_down.value
        env.torn_down_at = datetime.now(tz=timezone.utc)
        return env_repo.save(db, env)

    try:
        kc = crypto.decrypt(host.kubeconfig_encrypted)
        vcluster.teardown(
            host_kubeconfig_yaml=kc,
            host_context_name=host.context_name,
            namespace=env.namespace,
            vcluster_name=env.vcluster_name,
        )
    except Exception as e:
        log.exception("teardown failed for env %s", env.id)
        env.last_error = f"teardown: {type(e).__name__}: {e}"[:2000]
        # Mark torn_down anyway so the UI stops showing it as active; admins can
        # reconcile manually if needed.
    env.status = ValidationEnvStatus.torn_down.value
    env.torn_down_at = datetime.now(tz=timezone.utc)
    env = env_repo.save(db, env)
    history_service.record_event(
        db,
        request_id=env.request_id,
        actor_id=actor_id,
        event_type=HistoryEventType.validation_env_torn_down,
        detail={"env_id": env.id, "vcluster_name": env.vcluster_name},
    )
    return env
