"""Unit tests for the validation runner internals (Chunk 3).

Covers the pure pieces that don't need a cluster: status aggregation,
topological ordering, and the kubernetes_security analyzer. The runner's
end-to-end behavior is exercised in test_validation_run_api.py with a
fake executor.
"""

from __future__ import annotations

from app.domain.enums import (
    ApprovalImpact,
    FailurePolicy,
    ValidationRunStatus,
    ValidationSeverity,
    ValidationStepStatus,
)
from app.validation.executors.kubernetes_security import analyze_workloads
from app.validation.runner import topo_order
from app.validation.types import StepRollupInput, aggregate_run


# ---------------------------------------------------------------------------
# aggregate_run
# ---------------------------------------------------------------------------


def _r(status, policy):
    return StepRollupInput(status=status, failure_policy=policy)


def test_aggregate_all_passed():
    run, impact = aggregate_run(
        [_r(ValidationStepStatus.passed, FailurePolicy.block)]
    )
    assert run == ValidationRunStatus.passed
    assert impact == ApprovalImpact.none


def test_aggregate_failed_block_blocks():
    run, impact = aggregate_run(
        [
            _r(ValidationStepStatus.passed, FailurePolicy.warn),
            _r(ValidationStepStatus.failed, FailurePolicy.block),
        ]
    )
    assert run == ValidationRunStatus.failed
    assert impact == ApprovalImpact.blocked


def test_aggregate_failed_warn_warns():
    run, impact = aggregate_run([_r(ValidationStepStatus.failed, FailurePolicy.warn)])
    assert run == ValidationRunStatus.warning
    assert impact == ApprovalImpact.warning


def test_aggregate_failed_ignore_no_impact():
    run, impact = aggregate_run([_r(ValidationStepStatus.failed, FailurePolicy.ignore)])
    assert run == ValidationRunStatus.passed
    assert impact == ApprovalImpact.none


def test_aggregate_warning_step():
    run, impact = aggregate_run([_r(ValidationStepStatus.warning, FailurePolicy.block)])
    assert run == ValidationRunStatus.warning
    assert impact == ApprovalImpact.warning


def test_aggregate_skipped_is_neutral():
    run, impact = aggregate_run(
        [
            _r(ValidationStepStatus.skipped, FailurePolicy.block),
            _r(ValidationStepStatus.passed, FailurePolicy.block),
        ]
    )
    assert run == ValidationRunStatus.passed
    assert impact == ApprovalImpact.none


def test_aggregate_takes_worst():
    run, impact = aggregate_run(
        [
            _r(ValidationStepStatus.warning, FailurePolicy.warn),
            _r(ValidationStepStatus.failed, FailurePolicy.block),
            _r(ValidationStepStatus.passed, FailurePolicy.block),
        ]
    )
    assert run == ValidationRunStatus.failed
    assert impact == ApprovalImpact.blocked


# ---------------------------------------------------------------------------
# topo_order
# ---------------------------------------------------------------------------


def test_topo_order_respects_dependencies():
    steps = [
        {"name": "c", "dependsOn": ["a", "b"]},
        {"name": "a", "dependsOn": []},
        {"name": "b", "dependsOn": ["a"]},
    ]
    ordered = [s["name"] for s in topo_order(steps)]
    assert ordered.index("a") < ordered.index("b") < ordered.index("c")


def test_topo_order_stable_for_independent_steps():
    steps = [
        {"name": "a", "dependsOn": []},
        {"name": "b", "dependsOn": []},
    ]
    assert [s["name"] for s in topo_order(steps)] == ["a", "b"]


# ---------------------------------------------------------------------------
# kubernetes_security analyzer
# ---------------------------------------------------------------------------


def _container(**sc):
    return {
        "name": sc.pop("name", "api"),
        "image": sc.pop("image", "ghcr.io/example/app:latest"),
        "resources": sc.pop("resources", {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "256Mi"}}),
        "securityContext": {
            "privileged": sc.get("privileged"),
            "runAsUser": sc.get("runAsUser"),
            "runAsNonRoot": sc.get("runAsNonRoot"),
            "allowPrivilegeEscalation": sc.get("allowPrivilegeEscalation"),
            "readOnlyRootFilesystem": sc.get("readOnlyRootFilesystem"),
            "addedCapabilities": sc.get("addedCapabilities", []),
        },
    }


def _workload(containers, **kw):
    return {
        "owner": kw.get("owner", "deployment/rag-api"),
        "namespace": kw.get("namespace", "default"),
        "podName": kw.get("podName", "rag-api-abc"),
        "hostNetwork": kw.get("hostNetwork", False),
        "hostPID": kw.get("hostPID", False),
        "containers": containers,
        "initContainers": [],
        "volumes": kw.get("volumes", []),
    }


def test_clean_workload_passes():
    workloads = [_workload([_container()])]
    findings, severity, status, details = analyze_workloads(workloads, {})
    assert findings == []
    assert severity == ValidationSeverity.none
    assert status == ValidationStepStatus.passed


def test_privileged_container_is_high_and_fails():
    workloads = [_workload([_container(privileged=True)])]
    findings, severity, status, details = analyze_workloads(workloads, {})
    assert any(f["title"] == "Privileged container detected" for f in findings)
    assert severity == ValidationSeverity.high
    assert status == ValidationStepStatus.failed


def test_missing_limits_is_low_and_warns():
    workloads = [
        _workload([_container(resources={"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {}})])
    ]
    findings, severity, status, details = analyze_workloads(workloads, {})
    assert any(f["title"] == "Missing resource limits" for f in findings)
    assert severity == ValidationSeverity.low
    assert status == ValidationStepStatus.warning


def test_hostpath_and_hostnetwork_are_high():
    workloads = [
        _workload(
            [_container()],
            hostNetwork=True,
            volumes=[{"name": "data", "type": "hostPath", "hostPath": "/var/run"}],
        )
    ]
    findings, severity, status, details = analyze_workloads(workloads, {})
    titles = {f["title"] for f in findings}
    assert "Host network enabled" in titles
    assert "hostPath volume mounted" in titles
    assert status == ValidationStepStatus.failed


def test_run_as_root_detected():
    workloads = [_workload([_container(runAsUser=0)])]
    findings, severity, status, details = analyze_workloads(workloads, {})
    assert any(f["title"] == "Container runs as root" for f in findings)


def test_run_as_nonroot_not_flagged():
    workloads = [_workload([_container(runAsNonRoot=True)])]
    findings, _, _, _ = analyze_workloads(workloads, {})
    assert not any(f["title"] == "Container runs as root" for f in findings)


def test_risky_capabilities_flagged():
    workloads = [_workload([_container(addedCapabilities=["NET_ADMIN", "CHOWN"])])]
    findings, severity, status, _ = analyze_workloads(workloads, {})
    cap_findings = [f for f in findings if f["title"] == "Risky Linux capabilities added"]
    assert cap_findings
    assert "NET_ADMIN" in cap_findings[0]["message"]
    assert "CHOWN" not in cap_findings[0]["message"]  # not in risky set


def test_config_can_disable_checks():
    workloads = [_workload([_container()], hostNetwork=True)]
    findings, _, status, _ = analyze_workloads(workloads, {"warnIfHostNetwork": False})
    assert not any(f["title"] == "Host network enabled" for f in findings)
