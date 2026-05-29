"""builtin.kubernetes_security executor.

Inspects the workload inventory for risky Kubernetes configuration and
produces findings grouped by severity. Prefers an upstream
`builtin.workload_inventory` artifact; if none is available (e.g. the
step is run standalone), it collects the inventory itself.

The finding logic lives in `analyze_workloads`, a pure function over the
inventory's `workloads` list, so it's testable without a cluster.
"""
from __future__ import annotations

import json
from typing import Any

from app.domain.enums import ValidationSeverity, ValidationStepStatus
from app.validation import kube
from app.validation.executors.workload_inventory import INVENTORY_ARTIFACT_NAME
from app.validation.inventory import collect_inventory
from app.validation.types import ArtifactDraft, StepContext, StepOutcome

# Severity ordering for picking the step's overall severity.
_SEV_ORDER = [
    ValidationSeverity.none,
    ValidationSeverity.low,
    ValidationSeverity.medium,
    ValidationSeverity.high,
    ValidationSeverity.critical,
]


def _max_sev(a: ValidationSeverity, b: ValidationSeverity) -> ValidationSeverity:
    return max((a, b), key=_SEV_ORDER.index)


def _missing_limits(container: dict[str, Any]) -> bool:
    limits = container.get("resources", {}).get("limits", {})
    return not (limits.get("cpu") and limits.get("memory"))


def _missing_requests(container: dict[str, Any]) -> bool:
    requests = container.get("resources", {}).get("requests", {})
    return not (requests.get("cpu") and requests.get("memory"))


def _is_root(sc: dict[str, Any]) -> bool | None:
    """Return True if the container is detectably running as root, False if
    detectably non-root, None if undeterminable from the spec."""
    if sc.get("runAsNonRoot") is True:
        return False
    run_as_user = sc.get("runAsUser")
    if run_as_user is not None:
        return run_as_user == 0
    if sc.get("runAsNonRoot") is False:
        return True
    return None


def analyze_workloads(
    workloads: list[dict[str, Any]], config: dict[str, Any]
) -> tuple[list[dict[str, Any]], ValidationSeverity, ValidationStepStatus, dict[str, Any]]:
    """Produce (findings, severity, status, details) for a workloads list.

    `config` toggles mirror the default pipeline:
      - denyPrivilegedContainers (default True) → privileged is high severity
      - warnIfRunAsRoot (default True)
      - warnIfMissingResourceLimits (default True)
      - warnIfHostPathMounts (default True)
      - warnIfHostNetwork (default True)
    """
    deny_privileged = config.get("denyPrivilegedContainers", True)
    warn_root = config.get("warnIfRunAsRoot", True)
    warn_limits = config.get("warnIfMissingResourceLimits", True)
    warn_hostpath = config.get("warnIfHostPathMounts", True)
    warn_hostnet = config.get("warnIfHostNetwork", True)

    findings: list[dict[str, Any]] = []

    def add(severity: str, title: str, resource: str, message: str, recommendation: str) -> None:
        findings.append(
            {
                "severity": severity,
                "title": title,
                "resource": resource,
                "message": message,
                "recommendation": recommendation,
            }
        )

    for w in workloads:
        resource = w.get("owner") or f"pod/{w.get('podName')}"
        ns = w.get("namespace")
        res_label = f"{resource} (ns: {ns})" if ns else resource

        if warn_hostnet and w.get("hostNetwork"):
            add(
                "high",
                "Host network enabled",
                res_label,
                "Workload runs with hostNetwork=true, sharing the node's network namespace.",
                "Disable hostNetwork unless the workload genuinely requires node-level networking.",
            )
        if w.get("hostPID"):
            add(
                "high",
                "Host PID namespace enabled",
                res_label,
                "Workload runs with hostPID=true and can see all host processes.",
                "Disable hostPID unless absolutely required.",
            )
        if warn_hostpath:
            for v in w.get("volumes", []):
                if v.get("type") == "hostPath":
                    add(
                        "high",
                        "hostPath volume mounted",
                        res_label,
                        f"Volume '{v.get('name')}' mounts host path '{v.get('hostPath')}'.",
                        "Avoid hostPath mounts; use PVCs or projected volumes instead.",
                    )

        for c in w.get("containers", []) + w.get("initContainers", []):
            cname = c.get("name")
            sc = c.get("securityContext", {})
            cref = f"{res_label} / container {cname}"

            if sc.get("privileged") is True:
                add(
                    "high" if deny_privileged else "medium",
                    "Privileged container detected",
                    cref,
                    f"Container {cname} is configured with privileged=true.",
                    "Remove privileged mode unless absolutely required.",
                )
            if sc.get("allowPrivilegeEscalation") is True:
                add(
                    "medium",
                    "Privilege escalation allowed",
                    cref,
                    f"Container {cname} allows privilege escalation.",
                    "Set allowPrivilegeEscalation=false.",
                )
            if warn_root and _is_root(sc) is True:
                add(
                    "medium",
                    "Container runs as root",
                    cref,
                    f"Container {cname} runs (or may run) as UID 0.",
                    "Set runAsNonRoot=true and a non-zero runAsUser.",
                )
            if warn_limits and _missing_limits(c):
                add(
                    "low",
                    "Missing resource limits",
                    cref,
                    f"Container {cname} has no CPU and/or memory limits.",
                    "Set CPU and memory limits to bound resource usage.",
                )
            added_caps = sc.get("addedCapabilities") or []
            risky = sorted(set(added_caps) & {"SYS_ADMIN", "NET_ADMIN", "ALL", "NET_RAW", "SYS_PTRACE"})
            if risky:
                add(
                    "high",
                    "Risky Linux capabilities added",
                    cref,
                    f"Container {cname} adds capabilities: {', '.join(risky)}.",
                    "Drop unnecessary capabilities; avoid SYS_ADMIN / NET_ADMIN / ALL.",
                )

    # Roll up severity + counts.
    severity = ValidationSeverity.none
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f["severity"]
        counts[sev] = counts.get(sev, 0) + 1
        severity = _max_sev(severity, ValidationSeverity(sev))

    # Status: high/critical → failed; medium/low → warning; none → passed.
    if severity in (ValidationSeverity.high, ValidationSeverity.critical):
        status = ValidationStepStatus.failed
    elif severity in (ValidationSeverity.medium, ValidationSeverity.low):
        status = ValidationStepStatus.warning
    else:
        status = ValidationStepStatus.passed

    details = {"counts": counts, "findingsTotal": len(findings)}
    return findings, severity, status, details


def _load_upstream_workloads(ctx: StepContext) -> list[dict[str, Any]] | None:
    inv_outcome = ctx.upstream_of_type("builtin.workload_inventory")
    if inv_outcome is None:
        return None
    for art in inv_outcome.artifacts:
        if art.name == INVENTORY_ARTIFACT_NAME:
            try:
                return json.loads(art.content.decode("utf-8")).get("workloads")
            except (ValueError, UnicodeDecodeError):
                return None
    return None


def run(ctx: StepContext) -> StepOutcome:
    workloads = _load_upstream_workloads(ctx)
    if workloads is None:
        # No upstream inventory available — collect it ourselves.
        api = kube.api_client_from_kubeconfig(ctx.kubeconfig_yaml)
        workloads = collect_inventory(api, {}).get("workloads", [])

    findings, severity, status, details = analyze_workloads(workloads, ctx.config)

    if not findings:
        summary = "No Kubernetes security findings."
    else:
        c = details["counts"]
        parts = [f"{c[k]} {k}" for k in ("critical", "high", "medium", "low") if c.get(k)]
        summary = f"{len(findings)} finding(s): " + ", ".join(parts) + "."

    artifact = ArtifactDraft(
        name="kubernetes-security-findings.json",
        artifact_type="json",
        content=json.dumps({"findings": findings, "counts": details["counts"]}, indent=2).encode("utf-8"),
        content_type="application/json",
    )

    return StepOutcome(
        status=status,
        severity=severity,
        summary=summary,
        findings=findings,
        details=details,
        artifacts=[artifact],
    )
