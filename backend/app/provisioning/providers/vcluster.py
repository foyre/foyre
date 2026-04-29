"""vcluster provider — creates and tears down virtual clusters on a host cluster.

Implementation strategy:
  - Shell out to the `vcluster` CLI for create/delete (the CLI handles Helm
    chart rendering and installation for us).
  - Use the Kubernetes Python client for everything else: readiness polling,
    patching the Service to NodePort, reading the generated secret, looking
    up node IPs.

Wrapped behind `ProvisioningProvider` so alternate providers (K3k,
namespace-only, etc.) can be swapped in without touching callers.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass

import yaml
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException


@dataclass
class ProvisionResult:
    namespace: str
    vcluster_name: str
    external_endpoint: str  # e.g. "https://192.168.1.92:32242"
    user_kubeconfig: str


class ProvisionError(RuntimeError):
    pass


def _api_client_from_kubeconfig_yaml(
    kubeconfig_yaml: str, context_name: str | None
) -> k8s_client.ApiClient:
    conf_dict = yaml.safe_load(kubeconfig_yaml)
    configuration = k8s_client.Configuration()
    k8s_config.load_kube_config_from_dict(
        config_dict=conf_dict,
        context=context_name,
        client_configuration=configuration,
    )
    return k8s_client.ApiClient(configuration=configuration)


def _run_vcluster(kubeconfig_path: str, *args: str, timeout: int = 120) -> str:
    """Invoke the vcluster CLI. Returns stdout; raises ProvisionError on failure."""
    env = {**os.environ, "KUBECONFIG": kubeconfig_path}
    try:
        proc = subprocess.run(
            ["vcluster", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        raise ProvisionError(
            "`vcluster` CLI not found on PATH. Install https://www.vcluster.com"
        )
    except subprocess.TimeoutExpired:
        raise ProvisionError(f"vcluster {args[0]} timed out after {timeout}s")
    if proc.returncode != 0:
        raise ProvisionError(
            f"vcluster {args[0]} failed (rc={proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:500]}"
        )
    return proc.stdout


def _wait_pod_ready(
    core: k8s_client.CoreV1Api, namespace: str, pod_name: str, timeout: int = 180
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            pod = core.read_namespaced_pod(pod_name, namespace)
        except ApiException as e:
            if e.status == 404:
                time.sleep(2)
                continue
            raise ProvisionError(f"error polling pod: {e.status} {e.reason}")
        statuses = pod.status.container_statuses or []
        if statuses and all(s.ready for s in statuses):
            return
        time.sleep(2)
    raise ProvisionError(
        f"pod {namespace}/{pod_name} didn't become ready within {timeout}s"
    )


def _patch_service_nodeport(
    core: k8s_client.CoreV1Api, namespace: str, service_name: str
) -> int:
    """Patch the vcluster's Service to NodePort and return the allocated HTTPS nodePort."""
    body = {"spec": {"type": "NodePort"}}
    core.patch_namespaced_service(service_name, namespace, body)
    # Re-read to discover the assigned nodePort.
    svc = core.read_namespaced_service(service_name, namespace)
    for port in svc.spec.ports or []:
        # vcluster's HTTPS api port is named "https" (older versions) or is the one
        # mapping to 443. Prefer by name, fall back to matching by port=443.
        if port.name == "https" and port.node_port:
            return int(port.node_port)
    for port in svc.spec.ports or []:
        if port.port == 443 and port.node_port:
            return int(port.node_port)
    raise ProvisionError(
        f"could not find HTTPS nodePort on service {namespace}/{service_name}"
    )


def _node_internal_ip(core: k8s_client.CoreV1Api) -> str:
    """Return the first ready node's InternalIP. Used when external_node_host is unset."""
    nodes = core.list_node()
    for node in nodes.items:
        for addr in node.status.addresses or []:
            if addr.type == "InternalIP":
                return addr.address
    raise ProvisionError("no node InternalIP found on host cluster")


def _read_vcluster_kubeconfig(
    core: k8s_client.CoreV1Api, namespace: str, vcluster_name: str
) -> str:
    """Read the vc-<name> secret vcluster generates and decode its kubeconfig."""
    import base64

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            secret = core.read_namespaced_secret(
                f"vc-{vcluster_name}", namespace
            )
        except ApiException as e:
            if e.status != 404:
                raise ProvisionError(f"reading secret failed: {e.status} {e.reason}")
            time.sleep(2)
            continue
        data = (secret.data or {}).get("config")
        if data:
            return base64.b64decode(data).decode("utf-8")
        time.sleep(2)
    raise ProvisionError(
        f"secret vc-{vcluster_name} in {namespace} didn't surface a kubeconfig"
    )


def _rewrite_server(kubeconfig_yaml: str, new_server: str) -> str:
    """Replace the in-cluster `server:` URL with the externally-reachable one."""
    conf = yaml.safe_load(kubeconfig_yaml)
    for cluster in conf.get("clusters", []):
        if "cluster" in cluster:
            cluster["cluster"]["server"] = new_server
    return yaml.safe_dump(conf, default_flow_style=False)


def provision(
    host_kubeconfig_yaml: str,
    host_context_name: str | None,
    namespace: str,
    vcluster_name: str,
    external_node_host: str | None,
) -> ProvisionResult:
    """Create a vcluster on the host cluster and return a user-usable kubeconfig.

    Steps:
      1. vcluster create <name> -n <namespace>  (creates ns + installs vcluster chart).
      2. Wait for the <name>-0 pod to become ready.
      3. Patch the <name> Service to NodePort; record the assigned nodePort.
      4. Read the vc-<name> secret to obtain the API-server kubeconfig.
      5. Rewrite the kubeconfig's `server:` to the external NodePort endpoint.
    """
    # Materialize the host kubeconfig into a file for the CLI to read.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, prefix="foyre-host-"
    ) as f:
        f.write(host_kubeconfig_yaml)
        host_kubeconfig_path = f.name
    os.chmod(host_kubeconfig_path, 0o600)

    try:
        api = _api_client_from_kubeconfig_yaml(host_kubeconfig_yaml, host_context_name)
        core = k8s_client.CoreV1Api(api)

        # Step 1: create via CLI. The CLI creates the namespace if absent and installs
        # vcluster via Helm. `--connect=false` stops it from trying to port-forward.
        _run_vcluster(
            host_kubeconfig_path,
            "create", vcluster_name,
            "-n", namespace,
            "--connect=false",
            timeout=300,
        )

        # Step 2: wait for readiness.
        _wait_pod_ready(core, namespace, f"{vcluster_name}-0", timeout=300)

        # Step 3: expose via NodePort.
        nodeport = _patch_service_nodeport(core, namespace, vcluster_name)

        # Step 4: obtain the raw kubeconfig from the secret.
        raw_kc = _read_vcluster_kubeconfig(core, namespace, vcluster_name)

        # Step 5: rewrite `server:` to the external host:port.
        external_host = external_node_host or _node_internal_ip(core)
        endpoint = f"https://{external_host}:{nodeport}"
        user_kubeconfig = _rewrite_server(raw_kc, endpoint)

        return ProvisionResult(
            namespace=namespace,
            vcluster_name=vcluster_name,
            external_endpoint=endpoint,
            user_kubeconfig=user_kubeconfig,
        )
    finally:
        try:
            os.unlink(host_kubeconfig_path)
        except OSError:
            pass


def teardown(
    host_kubeconfig_yaml: str,
    host_context_name: str | None,
    namespace: str,
    vcluster_name: str,
) -> None:
    """Delete the vcluster. Deletes the namespace too — everything in it goes."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, prefix="foyre-host-"
    ) as f:
        f.write(host_kubeconfig_yaml)
        host_kubeconfig_path = f.name
    os.chmod(host_kubeconfig_path, 0o600)

    try:
        # `vcluster delete` also removes the namespace by default.
        _run_vcluster(
            host_kubeconfig_path,
            "delete", vcluster_name,
            "-n", namespace,
            timeout=120,
        )
    finally:
        try:
            os.unlink(host_kubeconfig_path)
        except OSError:
            pass
