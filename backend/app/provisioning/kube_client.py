"""Helpers for talking to a host Kubernetes cluster via a provided kubeconfig.

Currently only `test_connection` is exposed; future slices will add helpers for
vcluster create/delete / service patching / secret reading.
"""
from __future__ import annotations

from dataclasses import dataclass

import yaml
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException


@dataclass
class ConnectionTestResult:
    success: bool
    cluster_version: str | None = None
    node_count: int | None = None
    has_storage_class: bool | None = None
    can_create_namespaces: bool | None = None
    can_create_rbac: bool | None = None
    error: str | None = None


def _api_client_from_kubeconfig(
    kubeconfig_yaml: str, context_name: str | None
) -> k8s_client.ApiClient:
    try:
        conf_dict = yaml.safe_load(kubeconfig_yaml)
    except yaml.YAMLError as e:
        raise ValueError(f"kubeconfig is not valid YAML: {e}") from e
    if not isinstance(conf_dict, dict):
        raise ValueError("kubeconfig must be a YAML mapping")

    configuration = k8s_client.Configuration()
    # Load kubeconfig dict into a Configuration instance.
    k8s_config.load_kube_config_from_dict(
        config_dict=conf_dict,
        context=context_name,
        client_configuration=configuration,
    )
    return k8s_client.ApiClient(configuration=configuration)


def _can_i(
    authz: k8s_client.AuthorizationV1Api,
    verb: str,
    resource: str,
    api_group: str = "",
    namespace: str = "",
) -> bool:
    """Use SelfSubjectAccessReview to check RBAC without side-effects."""
    review = k8s_client.V1SelfSubjectAccessReview(
        spec=k8s_client.V1SelfSubjectAccessReviewSpec(
            resource_attributes=k8s_client.V1ResourceAttributes(
                verb=verb,
                resource=resource,
                group=api_group,
                namespace=namespace or None,
            ),
        )
    )
    try:
        res = authz.create_self_subject_access_review(review)
        return bool(res.status and res.status.allowed)
    except ApiException:
        return False


def test_connection(
    kubeconfig_yaml: str, context_name: str | None = None
) -> ConnectionTestResult:
    """Validate we can reach the cluster and have the permissions we need.

    Doesn't mutate the cluster; uses `SelfSubjectAccessReview` to check RBAC.
    """
    try:
        api = _api_client_from_kubeconfig(kubeconfig_yaml, context_name)
    except Exception as e:
        return ConnectionTestResult(success=False, error=f"invalid kubeconfig: {e}")

    try:
        version = k8s_client.VersionApi(api).get_code()
        cluster_version = getattr(version, "git_version", None) or getattr(
            version, "gitVersion", None
        )

        core = k8s_client.CoreV1Api(api)
        nodes = core.list_node(_request_timeout=10)
        node_count = len(nodes.items)

        storage = k8s_client.StorageV1Api(api)
        scs = storage.list_storage_class(_request_timeout=10)
        has_sc = len(scs.items) > 0

        authz = k8s_client.AuthorizationV1Api(api)
        can_ns = _can_i(authz, "create", "namespaces")
        can_rbac = _can_i(
            authz,
            "create",
            "clusterrolebindings",
            api_group="rbac.authorization.k8s.io",
        )

        return ConnectionTestResult(
            success=True,
            cluster_version=cluster_version,
            node_count=node_count,
            has_storage_class=has_sc,
            can_create_namespaces=can_ns,
            can_create_rbac=can_rbac,
        )
    except ApiException as e:
        return ConnectionTestResult(
            success=False,
            error=f"kubernetes API error: {e.status} {e.reason}".strip(),
        )
    except Exception as e:  # pragma: no cover — connectivity errors
        return ConnectionTestResult(success=False, error=f"{type(e).__name__}: {e}")
