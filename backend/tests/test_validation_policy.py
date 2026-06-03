"""Tests for the builtin.policy declarative tier (curated checks)."""

from __future__ import annotations

from app.domain.enums import ValidationSeverity, ValidationStepStatus
from app.validation.executors.policy import (
    _registry_allowed,
    _split_image,
    evaluate_policy,
)


# ---------------------------------------------------------------------------
# Synthetic inventory helpers
# ---------------------------------------------------------------------------


def _container(**sc):
    return {
        "name": sc.pop("name", "api"),
        "image": sc.pop("image", "ghcr.io/acme/app:1.2.3"),
        "resources": sc.pop(
            "resources",
            {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "256Mi"}},
        ),
        "securityContext": {
            "privileged": sc.get("privileged"),
            "addedCapabilities": sc.get("addedCapabilities", []),
        },
    }


def _workload(containers=None, **kw):
    return {
        "owner": kw.get("owner", "deployment/app"),
        "namespace": kw.get("namespace", "default"),
        "podName": kw.get("podName", "app-abc"),
        "labels": kw.get("labels", {}),
        "containers": containers if containers is not None else [_container()],
        "initContainers": kw.get("initContainers", []),
        "volumes": kw.get("volumes", []),
    }


# ---------------------------------------------------------------------------
# Image-ref helpers
# ---------------------------------------------------------------------------


def test_split_image_tag():
    assert _split_image("ghcr.io/acme/app:1.2.3") == ("ghcr.io/acme/app", "1.2.3", False)


def test_split_image_digest():
    ref, tag, dig = _split_image("redis@sha256:abcd")
    assert ref == "redis" and tag is None and dig is True


def test_split_image_no_tag():
    assert _split_image("redis") == ("redis", None, False)


def test_split_image_port_registry():
    # registry with a port must not be mistaken for a tag
    assert _split_image("reg.example.com:5000/app:v1") == ("reg.example.com:5000/app", "v1", False)


def test_registry_allowed():
    assert _registry_allowed("ghcr.io/acme/app:1", ["ghcr.io/acme"]) is True
    assert _registry_allowed("ghcr.io/other/app:1", ["ghcr.io/acme"]) is False
    assert _registry_allowed("redis:7", ["docker.io"]) is True  # implicit docker.io
    assert _registry_allowed("reg.example.com/app:1", ["reg.example.com"]) is True


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def test_default_checks_pass_clean_workload():
    wl = [_workload()]
    findings, severity, status, details = evaluate_policy(wl, {})
    assert findings == []
    assert status == ValidationStepStatus.passed
    assert set(details["checksRun"])  # default set ran


def test_no_privileged_containers():
    wl = [_workload([_container(privileged=True)])]
    findings, sev, status, _ = evaluate_policy(wl, {"checks": {"no_privileged_containers": {}}})
    assert any(f["title"] == "Privileged container" for f in findings)
    assert sev == ValidationSeverity.high
    assert status == ValidationStepStatus.failed


def test_require_resource_limits():
    wl = [_workload([_container(resources={"requests": {}, "limits": {}})])]
    findings, sev, status, _ = evaluate_policy(wl, {"checks": {"require_resource_limits": {}}})
    assert any(f["title"] == "Missing resource limits" for f in findings)
    assert status == ValidationStepStatus.warning  # low severity


def test_deny_latest_tag():
    wl = [_workload([_container(image="docker.io/library/redis:latest")])]
    findings, _, _, _ = evaluate_policy(wl, {"checks": {"deny_latest_tag": {}}})
    assert any(f["title"] == "Unpinned image tag" for f in findings)


def test_deny_latest_tag_allows_pinned_and_digest():
    wl = [
        _workload([_container(image="redis:7")]),
        _workload([_container(image="redis@sha256:deadbeef")]),
    ]
    findings, _, status, _ = evaluate_policy(wl, {"checks": {"deny_latest_tag": {}}})
    assert findings == []
    assert status == ValidationStepStatus.passed


def test_allowed_registries():
    wl = [_workload([_container(image="docker.io/library/redis:7")])]
    findings, _, _, _ = evaluate_policy(
        wl, {"checks": {"allowed_registries": {"registries": ["ghcr.io/acme"]}}}
    )
    assert any(f["title"] == "Image from disallowed registry" for f in findings)


def test_required_labels():
    wl = [_workload(labels={"team": "x"})]
    findings, _, _, _ = evaluate_policy(
        wl, {"checks": {"required_labels": {"labels": ["app.kubernetes.io/owner", "team"]}}}
    )
    assert len(findings) == 1
    assert "app.kubernetes.io/owner" in findings[0]["message"]
    assert "team" not in findings[0]["message"]


def test_banned_capabilities_default_set():
    wl = [_workload([_container(addedCapabilities=["NET_ADMIN", "CHOWN"])])]
    findings, sev, _, _ = evaluate_policy(wl, {"checks": {"banned_capabilities": {}}})
    assert any("NET_ADMIN" in f["message"] for f in findings)
    assert not any("CHOWN" in f["message"] for f in findings)  # not banned by default


def test_banned_capabilities_custom_set():
    wl = [_workload([_container(addedCapabilities=["CHOWN"])])]
    findings, _, _, _ = evaluate_policy(
        wl, {"checks": {"banned_capabilities": {"capabilities": ["CHOWN"]}}}
    )
    assert len(findings) == 1


def test_host_path_mounts():
    wl = [_workload(volumes=[{"name": "data", "type": "hostPath", "hostPath": "/var/run"}])]
    findings, _, status, _ = evaluate_policy(wl, {"checks": {"host_path_mounts": {}}})
    assert any(f["title"] == "hostPath volume mounted" for f in findings)
    assert status == ValidationStepStatus.failed


def test_severity_override():
    wl = [_workload([_container(privileged=True)])]
    findings, sev, status, _ = evaluate_policy(
        wl, {"checks": {"no_privileged_containers": {"severity": "medium"}}}
    )
    assert findings[0]["severity"] == "medium"
    assert status == ValidationStepStatus.warning


def test_unknown_check_recorded_not_fatal():
    wl = [_workload()]
    findings, _, status, details = evaluate_policy(wl, {"checks": {"does_not_exist": {}}})
    assert details.get("unknownChecks") == ["does_not_exist"]
    assert status == ValidationStepStatus.passed
