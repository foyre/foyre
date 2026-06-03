"""custom.kubernetes_job executor.

Runs an admin-provided container image as a Kubernetes Job *inside the
validation environment's vcluster* (using the decrypted user kubeconfig),
lets it inspect the workload, and ingests its normalized JSON result.

Contract for the custom container:
  - Input artifacts (e.g. workload-inventory.json) are mounted read-only
    at /foyre/input.
  - A scratch volume is mounted at /foyre/output (advisory; for the
    container's own use).
  - The container MUST print its normalized result as a single JSON
    object to stdout. Foyre reads the pod logs and extracts the last
    JSON object. Shape:
        {"status": "passed|warning|failed|error",
         "severity": "none|low|medium|high|critical",
         "summary": "...",
         "findings": [ {severity,title,resource,message,recommendation} ]}

Guardrails (the brief's security requirements):
  - Foyre builds the entire pod spec; admins only supply image / command /
    args / env. privileged, hostPath, hostNetwork, hostPID are never set.
  - The pod runs with automountServiceAccountToken=false, a hardened
    container securityContext (no privilege escalation, all capabilities
    dropped), and resource limits.
  - Only admins can author pipelines (and thus custom-job images); this
    executor merely runs what an admin already approved.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

from app.domain.enums import ValidationStepStatus
from app.validation import kube, results
from app.validation.executors.workload_inventory import INVENTORY_ARTIFACT_NAME
from app.validation.types import ArtifactDraft, StepContext, StepOutcome

logger = logging.getLogger(__name__)

_DEFAULT_NAMESPACE = "foyre-validation"
_INPUT_MOUNT = "/foyre/input"
_OUTPUT_MOUNT = "/foyre/output"
_DNS1123 = re.compile(r"[^a-z0-9-]+")


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------


def _dns1123_name(raw: str) -> str:
    name = _DNS1123.sub("-", raw.lower()).strip("-")
    return name[:63] or "job"


def job_name(run_id: int, step_name: str) -> str:
    return _dns1123_name(f"foyre-val-{run_id}-{step_name}")


def build_input_configmap(name: str, namespace: str, inputs: dict[str, str]) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": name, "namespace": namespace},
        "data": inputs,
    }


def build_job_manifest(
    *,
    name: str,
    namespace: str,
    image: str,
    command: list[str] | None,
    args: list[str] | None,
    env: dict[str, str] | None,
    configmap_name: str,
    timeout_seconds: int,
    resources: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a hardened Job manifest. Pure → unit-tested for guardrails."""
    container: dict[str, Any] = {
        "name": "validator",
        "image": image,
        "volumeMounts": [
            {"name": "foyre-input", "mountPath": _INPUT_MOUNT, "readOnly": True},
            {"name": "foyre-output", "mountPath": _OUTPUT_MOUNT},
        ],
        "securityContext": {
            "allowPrivilegeEscalation": False,
            "privileged": False,
            "readOnlyRootFilesystem": False,
            "capabilities": {"drop": ["ALL"]},
        },
        "resources": resources
        or {
            "requests": {"cpu": "100m", "memory": "128Mi"},
            "limits": {"cpu": "1", "memory": "512Mi"},
        },
    }
    if command:
        container["command"] = command
    if args:
        container["args"] = args
    if env:
        container["env"] = [{"name": k, "value": str(v)} for k, v in env.items()]

    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": timeout_seconds,
            "ttlSecondsAfterFinished": 300,
            "template": {
                "metadata": {"name": name},
                "spec": {
                    "restartPolicy": "Never",
                    # Never expose a service account token to a custom job.
                    "automountServiceAccountToken": False,
                    # Guardrails: never host-* anything.
                    "hostNetwork": False,
                    "hostPID": False,
                    "hostIPC": False,
                    "containers": [container],
                    "volumes": [
                        {"name": "foyre-input", "configMap": {"name": configmap_name}},
                        {"name": "foyre-output", "emptyDir": {}},
                    ],
                },
            },
        },
    }


# Back-compat shims: the result-resolution logic now lives in
# `app.validation.results`. These delegators keep the original public names
# working for callers/tests.
def parse_result_from_logs(logs: str):
    return results.extract_json_object(logs)


def normalize_result(result):
    return results.normalize_result_dict(result)


# ---------------------------------------------------------------------------
# Orchestration (integration path; not unit-tested without a cluster)
# ---------------------------------------------------------------------------


def _gather_inputs(ctx: StepContext) -> dict[str, str]:
    inputs: dict[str, str] = {}
    inv_outcome = ctx.upstream_of_type("builtin.workload_inventory")
    if inv_outcome:
        for art in inv_outcome.artifacts:
            if art.name == INVENTORY_ARTIFACT_NAME:
                try:
                    inputs[INVENTORY_ARTIFACT_NAME] = art.content.decode("utf-8")
                except UnicodeDecodeError:
                    pass
    # ConfigMaps must have at least one key; provide a placeholder otherwise.
    if not inputs:
        inputs["README"] = "No upstream artifacts were available for this run."
    return inputs


def _ensure_namespace(core: k8s_client.CoreV1Api, namespace: str) -> None:
    try:
        core.read_namespace(namespace)
    except ApiException as e:
        if e.status != 404:
            raise
        core.create_namespace(
            k8s_client.V1Namespace(metadata=k8s_client.V1ObjectMeta(name=namespace))
        )


def _wait_for_job(
    batch: k8s_client.BatchV1Api, name: str, namespace: str, timeout: int
) -> str:
    """Poll until the job succeeds/fails or the timeout elapses. Returns
    'succeeded' | 'failed' | 'timeout'."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            job = batch.read_namespaced_job_status(name, namespace)
        except ApiException:
            time.sleep(2)
            continue
        status = job.status
        if status and status.succeeded:
            return "succeeded"
        if status and status.failed:
            return "failed"
        time.sleep(3)
    return "timeout"


def _pod_logs(core: k8s_client.CoreV1Api, name: str, namespace: str) -> str:
    pods = core.list_namespaced_pod(namespace, label_selector=f"job-name={name}")
    if not pods.items:
        return ""
    pod_name = pods.items[0].metadata.name
    try:
        return core.read_namespaced_pod_log(pod_name, namespace) or ""
    except ApiException:
        return ""


def _main_container_terminated_state(
    core: k8s_client.CoreV1Api, name: str, namespace: str
) -> tuple[int | None, str | None]:
    """Return (exit_code, terminated_reason) for the job's main container.

    Used so result resolution can distinguish "ran and failed" (clean
    nonzero exit) from "couldn't run" (OOMKilled, etc.). Returns (None, None)
    when the state can't be read.
    """
    try:
        pods = core.list_namespaced_pod(namespace, label_selector=f"job-name={name}")
    except ApiException:
        return None, None
    if not pods.items:
        return None, None
    statuses = getattr(pods.items[0].status, "container_statuses", None) or []
    for st in statuses:
        if st.name != "validator":
            continue
        term = getattr(getattr(st, "state", None), "terminated", None)
        if term is not None:
            return getattr(term, "exit_code", None), getattr(term, "reason", None)
    return None, None


def _cleanup(batch, core, name: str, configmap_name: str, namespace: str) -> None:
    try:
        batch.delete_namespaced_job(
            name, namespace, propagation_policy="Background"
        )
    except ApiException:
        logger.warning("failed to delete job %s/%s", namespace, name)
    try:
        core.delete_namespaced_config_map(configmap_name, namespace)
    except ApiException:
        logger.warning("failed to delete configmap %s/%s", namespace, configmap_name)


def run(ctx: StepContext) -> StepOutcome:
    config = ctx.config
    image = config.get("image")
    if not image:
        return StepOutcome(
            status=ValidationStepStatus.error,
            summary="custom.kubernetes_job is missing config.image.",
            error_message="config.image is required",
        )

    namespace = config.get("namespace") or _DEFAULT_NAMESPACE
    name = job_name(ctx.run_id, ctx.step_name)
    cm_name = f"{name}-input"[:63]
    timeout = int(ctx.step.get("timeoutSeconds", 300))

    try:
        api = kube.api_client_from_kubeconfig(ctx.kubeconfig_yaml)
        core = k8s_client.CoreV1Api(api)
        batch = k8s_client.BatchV1Api(api)

        _ensure_namespace(core, namespace)

        inputs = _gather_inputs(ctx)
        core.create_namespaced_config_map(
            namespace, build_input_configmap(cm_name, namespace, inputs)
        )

        manifest = build_job_manifest(
            name=name,
            namespace=namespace,
            image=image,
            command=config.get("command"),
            args=config.get("args"),
            env=config.get("env"),
            configmap_name=cm_name,
            timeout_seconds=timeout,
            resources=config.get("resources"),
        )
        batch.create_namespaced_job(namespace, manifest)

        outcome_state = _wait_for_job(batch, name, namespace, timeout)
        logs = _pod_logs(core, name, namespace)
        exit_code, terminated_reason = _main_container_terminated_state(
            core, name, namespace
        )
    except ApiException as e:
        return StepOutcome(
            status=ValidationStepStatus.error,
            summary="Failed to run custom validation job.",
            error_message=f"kubernetes error: {e.status} {e.reason}",
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("custom job step failed")
        return StepOutcome(
            status=ValidationStepStatus.error,
            summary="Failed to run custom validation job.",
            error_message=f"{type(e).__name__}: {e}"[:2000],
        )
    finally:
        try:
            _cleanup(batch, core, name, cm_name, namespace)  # type: ignore[possibly-undefined]
        except Exception:  # noqa: BLE001
            pass

    artifacts = [
        ArtifactDraft(
            name="job-logs.txt",
            artifact_type="log",
            content=(logs or "").encode("utf-8"),
            content_type="text/plain",
        )
    ]

    # Resolve via precedence: result.json (not available until the uploader
    # sidecar lands) → stdout JSON → exit code. A plain container that exits
    # 0 now passes instead of erroring (the relaxed contract).
    resolved = results.resolve_outcome(
        job_state=outcome_state,
        exit_code=exit_code,
        terminated_reason=terminated_reason,
        stdout=logs,
        result_json_bytes=None,
    )

    if resolved.result_obj is not None:
        artifacts.append(
            ArtifactDraft(
                name="custom-result.json",
                artifact_type="json",
                content=json.dumps(resolved.result_obj, indent=2).encode("utf-8"),
                content_type="application/json",
            )
        )

    return StepOutcome(
        status=resolved.status,
        severity=resolved.severity,
        summary=resolved.summary or f"Custom job completed ({outcome_state}).",
        findings=resolved.findings,
        details={
            "jobState": outcome_state,
            "exitCode": exit_code,
            "resultSource": resolved.source,
        },
        artifacts=artifacts,
        error_message=resolved.error_message,
    )
