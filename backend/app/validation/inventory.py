"""Collect a non-secret inventory of workloads in a validation environment.

Used by the `builtin.workload_inventory` step, and re-used by
`builtin.kubernetes_security` as a fallback when it runs without an
upstream inventory.

SECURITY: this module deliberately collects only *metadata*. It records
Secret and ConfigMap names but never their `.data`. Container env values
are not collected. The output is safe to persist as an artifact and show
to anyone who can see the request.
"""
from __future__ import annotations

import fnmatch
from typing import Any

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

from app.validation.kube import default_request_timeout

_TIMEOUT = default_request_timeout()


# ---------------------------------------------------------------------------
# Namespace selection
# ---------------------------------------------------------------------------


def _select_namespaces(
    core: k8s_client.CoreV1Api, include: list[str], exclude: list[str]
) -> list[str]:
    try:
        ns_list = core.list_namespace(_request_timeout=_TIMEOUT)
    except ApiException:
        return []
    names = [ns.metadata.name for ns in ns_list.items if ns.metadata and ns.metadata.name]
    include = include or ["*"]
    selected = []
    for name in names:
        if not any(fnmatch.fnmatchcase(name, pat) for pat in include):
            continue
        if any(fnmatch.fnmatchcase(name, pat) for pat in exclude):
            continue
        selected.append(name)
    return sorted(selected)


# ---------------------------------------------------------------------------
# Container / volume extraction
# ---------------------------------------------------------------------------


def _dict_or_empty(v: Any) -> dict[str, Any]:
    return dict(v) if isinstance(v, dict) else {}


def _container_info(container: Any, pod_run_as_user: Any, pod_run_as_non_root: Any) -> dict[str, Any]:
    sc = getattr(container, "security_context", None)
    caps = getattr(sc, "capabilities", None) if sc else None
    resources = getattr(container, "resources", None)
    requests = _dict_or_empty(getattr(resources, "requests", None)) if resources else {}
    limits = _dict_or_empty(getattr(resources, "limits", None)) if resources else {}

    run_as_user = getattr(sc, "run_as_user", None) if sc else None
    if run_as_user is None:
        run_as_user = pod_run_as_user
    run_as_non_root = getattr(sc, "run_as_non_root", None) if sc else None
    if run_as_non_root is None:
        run_as_non_root = pod_run_as_non_root

    return {
        "name": getattr(container, "name", None),
        "image": getattr(container, "image", None),
        "resources": {"requests": requests, "limits": limits},
        "securityContext": {
            "privileged": getattr(sc, "privileged", None) if sc else None,
            "runAsUser": run_as_user,
            "runAsNonRoot": run_as_non_root,
            "allowPrivilegeEscalation": getattr(sc, "allow_privilege_escalation", None) if sc else None,
            "readOnlyRootFilesystem": getattr(sc, "read_only_root_filesystem", None) if sc else None,
            "addedCapabilities": list(getattr(caps, "add", None) or []) if caps else [],
        },
    }


# Map of V1Volume attribute -> friendly volume type name. Only the source
# that is set is non-None on a volume.
_VOLUME_SOURCE_ATTRS = {
    "host_path": "hostPath",
    "empty_dir": "emptyDir",
    "config_map": "configMap",
    "secret": "secret",
    "persistent_volume_claim": "persistentVolumeClaim",
    "projected": "projected",
    "downward_api": "downwardAPI",
    "nfs": "nfs",
    "csi": "csi",
}


def _volume_info(volume: Any) -> dict[str, Any]:
    vtype = "unknown"
    host_path = None
    for attr, friendly in _VOLUME_SOURCE_ATTRS.items():
        if getattr(volume, attr, None) is not None:
            vtype = friendly
            if attr == "host_path":
                host_path = getattr(getattr(volume, attr), "path", None)
            break
    return {"name": getattr(volume, "name", None), "type": vtype, "hostPath": host_path}


def _owner_label(pod: Any) -> str:
    """Best-effort human label for the pod's owning workload.

    Pods owned by a ReplicaSet are relabeled as `deployment/<name>` by
    stripping the ReplicaSet's hash suffix — a heuristic that produces the
    friendly names reviewers expect without extra API round-trips.
    """
    meta = getattr(pod, "metadata", None)
    refs = getattr(meta, "owner_references", None) or []
    if refs:
        owner = refs[0]
        kind = getattr(owner, "kind", "") or ""
        name = getattr(owner, "name", "") or ""
        if kind == "ReplicaSet" and "-" in name:
            return f"deployment/{name.rsplit('-', 1)[0]}"
        if kind:
            return f"{kind.lower()}/{name}"
    name = getattr(meta, "name", "") if meta else ""
    return f"pod/{name}"


# ---------------------------------------------------------------------------
# Top-level collection
# ---------------------------------------------------------------------------


def collect_inventory(api_client: k8s_client.ApiClient, config: dict[str, Any]) -> dict[str, Any]:
    """Enumerate workloads + metadata in the selected namespaces.

    `config` honors `includeNamespaces` (glob list, default ["*"]) and
    `excludeNamespaces` (glob list).
    """
    core = k8s_client.CoreV1Api(api_client)
    apps = k8s_client.AppsV1Api(api_client)
    batch = k8s_client.BatchV1Api(api_client)
    networking = k8s_client.NetworkingV1Api(api_client)

    include = config.get("includeNamespaces") or ["*"]
    exclude = config.get("excludeNamespaces") or []
    namespaces = _select_namespaces(core, include, exclude)
    ns_set = set(namespaces)

    def _in_scope(obj: Any) -> bool:
        meta = getattr(obj, "metadata", None)
        return bool(meta and meta.namespace in ns_set)

    workloads: list[dict[str, Any]] = []
    images: set[str] = set()
    container_count = 0
    init_container_count = 0

    # Pods are the ground truth for running containers + resolved security.
    try:
        pods = core.list_pod_for_all_namespaces(_request_timeout=_TIMEOUT)
        pod_items = [p for p in pods.items if _in_scope(p)]
    except ApiException:
        pod_items = []

    for pod in pod_items:
        spec = getattr(pod, "spec", None)
        meta = getattr(pod, "metadata", None)
        pod_sc = getattr(spec, "security_context", None) if spec else None
        pod_run_as_user = getattr(pod_sc, "run_as_user", None) if pod_sc else None
        pod_run_as_non_root = getattr(pod_sc, "run_as_non_root", None) if pod_sc else None

        containers = list(getattr(spec, "containers", None) or []) if spec else []
        init_containers = list(getattr(spec, "init_containers", None) or []) if spec else []

        c_infos = [_container_info(c, pod_run_as_user, pod_run_as_non_root) for c in containers]
        i_infos = [_container_info(c, pod_run_as_user, pod_run_as_non_root) for c in init_containers]
        for ci in c_infos + i_infos:
            if ci.get("image"):
                images.add(ci["image"])
        container_count += len(c_infos)
        init_container_count += len(i_infos)

        volumes = [_volume_info(v) for v in (getattr(spec, "volumes", None) or [])] if spec else []

        workloads.append(
            {
                "owner": _owner_label(pod),
                "namespace": getattr(meta, "namespace", None) if meta else None,
                "podName": getattr(meta, "name", None) if meta else None,
                # Pod labels (metadata only) — used by the policy step's
                # required_labels check and useful evidence in general.
                "labels": dict(getattr(meta, "labels", None) or {}) if meta else {},
                "serviceAccountName": getattr(spec, "service_account_name", None) if spec else None,
                "hostNetwork": bool(getattr(spec, "host_network", False)) if spec else False,
                "hostPID": bool(getattr(spec, "host_pid", False)) if spec else False,
                "containers": c_infos,
                "initContainers": i_infos,
                "volumes": volumes,
            }
        )

    # Controller counts (best-effort; each wrapped so a missing API doesn't
    # abort the whole inventory).
    def _count(list_fn) -> int:
        try:
            res = list_fn(_request_timeout=_TIMEOUT)
            return len([x for x in res.items if _in_scope(x)])
        except ApiException:
            return 0
        except Exception:  # noqa: BLE001 - defensive against client quirks
            return 0

    counts = {
        "deployments": _count(apps.list_deployment_for_all_namespaces),
        "statefulsets": _count(apps.list_stateful_set_for_all_namespaces),
        "daemonsets": _count(apps.list_daemon_set_for_all_namespaces),
        "jobs": _count(batch.list_job_for_all_namespaces),
        "cronjobs": _count(batch.list_cron_job_for_all_namespaces),
        "pods": len(pod_items),
        "services": _count(core.list_service_for_all_namespaces),
        "ingresses": _count(networking.list_ingress_for_all_namespaces),
        "serviceAccounts": _count(core.list_service_account_for_all_namespaces),
        "containers": container_count,
        "initContainers": init_container_count,
    }

    # Names/metadata only — never values.
    def _name_meta(list_fn) -> list[dict[str, str]]:
        try:
            res = list_fn(_request_timeout=_TIMEOUT)
        except Exception:  # noqa: BLE001
            return []
        out = []
        for x in res.items:
            if not _in_scope(x):
                continue
            m = x.metadata
            out.append({"namespace": m.namespace, "name": m.name})
        return out

    config_maps = _name_meta(core.list_config_map_for_all_namespaces)
    secrets = _name_meta(core.list_secret_for_all_namespaces)
    counts["configMaps"] = len(config_maps)
    counts["secrets"] = len(secrets)

    security_summary = _light_security_summary(workloads)

    return {
        "namespaces": namespaces,
        "counts": counts,
        "images": sorted(images),
        "workloads": workloads,
        "configMaps": config_maps,
        "secrets": secrets,
        "security": security_summary,
    }


def _container_missing_limits(c: dict[str, Any]) -> bool:
    limits = c.get("resources", {}).get("limits", {})
    return not (limits.get("cpu") and limits.get("memory"))


def _container_missing_requests(c: dict[str, Any]) -> bool:
    requests = c.get("resources", {}).get("requests", {})
    return not (requests.get("cpu") and requests.get("memory"))


def _light_security_summary(workloads: list[dict[str, Any]]) -> dict[str, int]:
    """Quick counts for the inventory result's `details`. The
    kubernetes_security step produces the detailed, per-resource findings."""
    privileged = host_path = host_network = missing_limits = missing_requests = 0
    for w in workloads:
        if w.get("hostNetwork"):
            host_network += 1
        if any(v.get("type") == "hostPath" for v in w.get("volumes", [])):
            host_path += 1
        for c in w.get("containers", []) + w.get("initContainers", []):
            sc = c.get("securityContext", {})
            if sc.get("privileged") is True:
                privileged += 1
            if _container_missing_limits(c):
                missing_limits += 1
            if _container_missing_requests(c):
                missing_requests += 1
    return {
        "privilegedContainers": privileged,
        "hostPathMounts": host_path,
        "hostNetwork": host_network,
        "containersMissingLimits": missing_limits,
        "containersMissingRequests": missing_requests,
    }
