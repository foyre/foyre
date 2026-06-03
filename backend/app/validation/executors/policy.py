"""builtin.policy executor — curated, declarative policy checks.

Tier 1 of the extensibility model (see docs/dev/validation-extensibility-design.md):
no code, no container. Admins enable/configure a curated set of named
checks that evaluate the **workload inventory** (not the live cluster), so
the step is deterministic and unit-testable.

Config shape:

    config:
      checks:
        no_privileged_containers: { severity: high }
        require_resource_limits:  { severity: low }
        deny_latest_tag:          { severity: medium }
        allowed_registries:
          severity: high
          registries: ["registry.example.com", "ghcr.io/acme"]
        required_labels:
          severity: low
          labels: ["app.kubernetes.io/owner"]
        banned_capabilities:
          severity: high
          capabilities: ["SYS_ADMIN", "NET_ADMIN", "ALL"]
        host_path_mounts: { severity: high }

If `checks` is omitted, a sensible default set runs. Each check's
`severity` can be overridden in its params.

This is intentionally NOT an expression language. A future
`builtin.policy_engine` (CEL/OPA) can offer arbitrary expressions; this
step covers the common 80% with zero learning curve.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from app.domain.enums import ValidationSeverity, ValidationStepStatus
from app.validation import kube
from app.validation.executors.workload_inventory import INVENTORY_ARTIFACT_NAME
from app.validation.inventory import collect_inventory
from app.validation.types import ArtifactDraft, StepContext, StepOutcome

Finding = dict[str, Any]
# A check takes the inventory's workloads list + its params and returns findings.
CheckFn = Callable[[list[dict[str, Any]], dict[str, Any]], list[Finding]]

_SEV_ORDER = [
    ValidationSeverity.none,
    ValidationSeverity.low,
    ValidationSeverity.medium,
    ValidationSeverity.high,
    ValidationSeverity.critical,
]

# Default severity per check (overridable via params.severity).
_DEFAULT_SEVERITY = {
    "no_privileged_containers": "high",
    "require_resource_limits": "low",
    "deny_latest_tag": "medium",
    "allowed_registries": "high",
    "required_labels": "low",
    "banned_capabilities": "high",
    "host_path_mounts": "high",
}

# Checks enabled when `config.checks` is omitted entirely.
_DEFAULT_CHECKS = [
    "no_privileged_containers",
    "require_resource_limits",
    "deny_latest_tag",
    "host_path_mounts",
    "banned_capabilities",
]

_DEFAULT_BANNED_CAPS = ["SYS_ADMIN", "NET_ADMIN", "ALL", "SYS_PTRACE", "NET_RAW"]


# ---------------------------------------------------------------------------
# Image-reference helpers
# ---------------------------------------------------------------------------


def _split_image(image: str) -> tuple[str, str | None, bool]:
    """Return (ref_without_tag_or_digest, tag_or_None, has_digest)."""
    if "@" in image:
        return image.split("@", 1)[0], None, True
    slash = image.rfind("/")
    colon = image.rfind(":")
    if colon > slash:
        return image[:colon], image[colon + 1 :], False
    return image, None, False


def _registry_host(image: str) -> str:
    ref, _, _ = _split_image(image)
    first = ref.split("/", 1)[0]
    if "." in first or ":" in first or first == "localhost":
        return first
    return "docker.io"


def _registry_allowed(image: str, allowed: list[str]) -> bool:
    ref, _, _ = _split_image(image)
    host = _registry_host(image)
    for a in allowed:
        a = a.rstrip("/")
        if ref == a or ref.startswith(a + "/") or host == a:
            return True
    return False


# ---------------------------------------------------------------------------
# Helpers shared by checks
# ---------------------------------------------------------------------------


def _resource(w: dict[str, Any]) -> str:
    res = w.get("owner") or f"pod/{w.get('podName')}"
    ns = w.get("namespace")
    return f"{res} (ns: {ns})" if ns else res


def _all_containers(w: dict[str, Any]) -> list[dict[str, Any]]:
    return list(w.get("containers", [])) + list(w.get("initContainers", []))


def _sev(params: dict[str, Any], check_name: str) -> str:
    return params.get("severity") or _DEFAULT_SEVERITY.get(check_name, "medium")


# ---------------------------------------------------------------------------
# The curated checks
# ---------------------------------------------------------------------------


def _check_no_privileged(workloads, params):
    sev = _sev(params, "no_privileged_containers")
    out = []
    for w in workloads:
        for c in _all_containers(w):
            if c.get("securityContext", {}).get("privileged") is True:
                out.append({
                    "severity": sev,
                    "title": "Privileged container",
                    "resource": f"{_resource(w)} / container {c.get('name')}",
                    "message": f"Container {c.get('name')} runs privileged.",
                    "recommendation": "Remove privileged mode unless strictly required.",
                })
    return out


def _check_require_limits(workloads, params):
    sev = _sev(params, "require_resource_limits")
    out = []
    for w in workloads:
        for c in _all_containers(w):
            limits = c.get("resources", {}).get("limits", {})
            if not (limits.get("cpu") and limits.get("memory")):
                out.append({
                    "severity": sev,
                    "title": "Missing resource limits",
                    "resource": f"{_resource(w)} / container {c.get('name')}",
                    "message": f"Container {c.get('name')} lacks CPU and/or memory limits.",
                    "recommendation": "Set CPU and memory limits to bound resource usage.",
                })
    return out


def _check_deny_latest_tag(workloads, params):
    sev = _sev(params, "deny_latest_tag")
    out = []
    seen = set()
    for w in workloads:
        for c in _all_containers(w):
            image = c.get("image")
            if not image or image in seen:
                continue
            seen.add(image)
            ref, tag, has_digest = _split_image(image)
            if has_digest:
                continue
            if tag is None or tag == "latest":
                out.append({
                    "severity": sev,
                    "title": "Unpinned image tag",
                    "resource": image,
                    "message": f"Image '{image}' uses a mutable/implicit 'latest' tag.",
                    "recommendation": "Pin a specific version tag or a digest.",
                })
    return out


def _check_allowed_registries(workloads, params):
    allowed = params.get("registries") or []
    sev = _sev(params, "allowed_registries")
    out = []
    seen = set()
    for w in workloads:
        for c in _all_containers(w):
            image = c.get("image")
            if not image or image in seen:
                continue
            seen.add(image)
            if not _registry_allowed(image, allowed):
                out.append({
                    "severity": sev,
                    "title": "Image from disallowed registry",
                    "resource": image,
                    "message": f"Image '{image}' is not from an allowed registry.",
                    "recommendation": f"Use an approved registry: {allowed}.",
                })
    return out


def _check_required_labels(workloads, params):
    required = params.get("labels") or []
    sev = _sev(params, "required_labels")
    out = []
    for w in workloads:
        labels = w.get("labels", {}) or {}
        missing = [k for k in required if k not in labels]
        if missing:
            out.append({
                "severity": sev,
                "title": "Missing required labels",
                "resource": _resource(w),
                "message": f"Missing label(s): {', '.join(missing)}.",
                "recommendation": "Add the required labels to this workload.",
            })
    return out


def _check_banned_capabilities(workloads, params):
    banned = set(params.get("capabilities") or _DEFAULT_BANNED_CAPS)
    sev = _sev(params, "banned_capabilities")
    out = []
    for w in workloads:
        for c in _all_containers(w):
            added = set(c.get("securityContext", {}).get("addedCapabilities") or [])
            hit = sorted(added & banned)
            if hit:
                out.append({
                    "severity": sev,
                    "title": "Banned Linux capabilities added",
                    "resource": f"{_resource(w)} / container {c.get('name')}",
                    "message": f"Container {c.get('name')} adds banned capabilities: {', '.join(hit)}.",
                    "recommendation": "Drop these capabilities.",
                })
    return out


def _check_host_path_mounts(workloads, params):
    sev = _sev(params, "host_path_mounts")
    out = []
    for w in workloads:
        for v in w.get("volumes", []):
            if v.get("type") == "hostPath":
                out.append({
                    "severity": sev,
                    "title": "hostPath volume mounted",
                    "resource": _resource(w),
                    "message": f"Volume '{v.get('name')}' mounts host path '{v.get('hostPath')}'.",
                    "recommendation": "Avoid hostPath; use PVCs or projected volumes.",
                })
    return out


_CHECKS: dict[str, CheckFn] = {
    "no_privileged_containers": _check_no_privileged,
    "require_resource_limits": _check_require_limits,
    "deny_latest_tag": _check_deny_latest_tag,
    "allowed_registries": _check_allowed_registries,
    "required_labels": _check_required_labels,
    "banned_capabilities": _check_banned_capabilities,
    "host_path_mounts": _check_host_path_mounts,
}


# ---------------------------------------------------------------------------
# Pure evaluation
# ---------------------------------------------------------------------------


def evaluate_policy(
    workloads: list[dict[str, Any]], config: dict[str, Any]
) -> tuple[list[Finding], ValidationSeverity, ValidationStepStatus, dict[str, Any]]:
    """Run the configured checks over `workloads`. Pure → unit-tested."""
    checks_cfg = config.get("checks")
    if checks_cfg is None:
        checks_cfg = {name: {} for name in _DEFAULT_CHECKS}

    findings: list[Finding] = []
    ran: list[str] = []
    unknown: list[str] = []

    for name, params in checks_cfg.items():
        fn = _CHECKS.get(name)
        if fn is None:
            unknown.append(name)
            continue
        ran.append(name)
        findings.extend(fn(workloads, params or {}))

    severity = ValidationSeverity.none
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        s = f["severity"]
        counts[s] = counts.get(s, 0) + 1
        severity = max((severity, ValidationSeverity(s)), key=_SEV_ORDER.index)

    if severity in (ValidationSeverity.high, ValidationSeverity.critical):
        status = ValidationStepStatus.failed
    elif severity in (ValidationSeverity.medium, ValidationSeverity.low):
        status = ValidationStepStatus.warning
    else:
        status = ValidationStepStatus.passed

    details = {"checksRun": ran, "counts": counts, "findingsTotal": len(findings)}
    if unknown:
        details["unknownChecks"] = unknown
    return findings, severity, status, details


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


def _load_upstream_workloads(ctx: StepContext) -> list[dict[str, Any]] | None:
    inv = ctx.upstream_of_type("builtin.workload_inventory")
    if inv is None:
        return None
    for art in inv.artifacts:
        if art.name == INVENTORY_ARTIFACT_NAME:
            try:
                return json.loads(art.content.decode("utf-8")).get("workloads")
            except (ValueError, UnicodeDecodeError):
                return None
    return None


def run(ctx: StepContext) -> StepOutcome:
    workloads = _load_upstream_workloads(ctx)
    if workloads is None:
        api = kube.api_client_from_kubeconfig(ctx.kubeconfig_yaml)
        workloads = collect_inventory(api, {}).get("workloads", [])

    findings, severity, status, details = evaluate_policy(workloads, ctx.config)

    if not findings:
        summary = "All policy checks passed."
    else:
        c = details["counts"]
        parts = [f"{c[k]} {k}" for k in ("critical", "high", "medium", "low") if c.get(k)]
        summary = f"{len(findings)} policy finding(s): " + ", ".join(parts) + "."

    artifact = ArtifactDraft(
        name="policy-results.json",
        artifact_type="json",
        content=json.dumps({"findings": findings, **details}, indent=2).encode("utf-8"),
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
