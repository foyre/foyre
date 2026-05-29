"""Build Kubernetes API clients from a kubeconfig YAML string.

Mirrors the helper in `app.provisioning.providers.vcluster` but is shared
across step executors that need to talk to a validation environment's
vcluster using the (decrypted) user kubeconfig.

A short default request timeout is applied so a single hung API call
can't pin a step past its own timeout budget — the runner also enforces
a per-step wall-clock timeout on top of this.
"""
from __future__ import annotations

import yaml
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

# Per-request timeout (connect, read) in seconds for individual API calls.
_DEFAULT_REQUEST_TIMEOUT = 30


def api_client_from_kubeconfig(
    kubeconfig_yaml: str, context_name: str | None = None
) -> k8s_client.ApiClient:
    """Return an ApiClient configured from an in-memory kubeconfig."""
    conf_dict = yaml.safe_load(kubeconfig_yaml)
    configuration = k8s_client.Configuration()
    k8s_config.load_kube_config_from_dict(
        config_dict=conf_dict,
        context=context_name,
        client_configuration=configuration,
    )
    return k8s_client.ApiClient(configuration=configuration)


def default_request_timeout() -> int:
    return _DEFAULT_REQUEST_TIMEOUT
