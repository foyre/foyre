"""Tests for image scanning + custom-job step logic (Chunk 4).

The cluster/subprocess boundaries are stubbed: Trivy JSON parsing is
exercised on canned output, the image-scan executor uses a fake scanner,
and the custom-job pure helpers (manifest builder, log parser, result
normalizer) are tested directly.
"""

from __future__ import annotations

import json

from app.domain.enums import ValidationSeverity, ValidationStepStatus
from app.validation.executors import image_scan
from app.validation.executors import kubernetes_job
from app.validation.scanners import get_scanner, register
from app.validation.scanners.base import ScanResult, VulnerabilityCounts
from app.validation.scanners.trivy import TrivyScanner
from app.validation.types import StepContext


# ---------------------------------------------------------------------------
# Trivy JSON parsing
# ---------------------------------------------------------------------------


def test_trivy_parse_counts_by_severity():
    raw = json.dumps(
        {
            "Results": [
                {
                    "Vulnerabilities": [
                        {"Severity": "CRITICAL"},
                        {"Severity": "HIGH"},
                        {"Severity": "high"},
                        {"Severity": "MEDIUM"},
                        {"Severity": "LOW"},
                        {"Severity": "WEIRD"},
                    ]
                },
                {"Vulnerabilities": None},
                {},
            ]
        }
    ).encode()
    counts = TrivyScanner.parse(raw)
    assert counts.critical == 1
    assert counts.high == 2
    assert counts.medium == 1
    assert counts.low == 1
    assert counts.unknown == 1


def test_trivy_parse_empty():
    counts = TrivyScanner.parse(b"{}")
    assert counts.as_dict() == {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}


def test_trivy_registered_by_default():
    assert get_scanner("trivy") is not None


# ---------------------------------------------------------------------------
# image_scan executor (with a fake scanner)
# ---------------------------------------------------------------------------


class _FakeScanner:
    def __init__(self, name, counts: VulnerabilityCounts):
        self.name = name
        self._counts = counts

    def scan(self, image, config):
        return ScanResult(image=image, success=True, counts=self._counts, raw=b'{"fake":true}')


def _ctx_with_images(monkeypatch, images, config):
    # Bypass the cluster: image_scan reads images from upstream details.
    from app.validation.types import StepOutcome

    inv = StepOutcome(
        status=ValidationStepStatus.passed,
        details={"images": images},
    )
    step = {"name": "image-scan", "type": "builtin.image_scan", "config": config, "dependsOn": ["inv"]}
    ctx = StepContext(
        run_id=1,
        step=step,
        kubeconfig_yaml="fake",
        upstream={"inv": inv},
        upstream_type_map={"inv": "builtin.workload_inventory"},
    )
    return ctx


def test_image_scan_critical_fails(monkeypatch):
    register(_FakeScanner("trivy", VulnerabilityCounts(critical=2, high=1)))
    try:
        ctx = _ctx_with_images(monkeypatch, ["img:a"], {"failOnCritical": True, "warnOnHigh": True})
        out = image_scan.run(ctx)
        assert out.status == ValidationStepStatus.failed
        assert out.severity == ValidationSeverity.critical
        assert any(f["severity"] == "critical" for f in out.findings)
        # raw per-image artifact + summary artifact.
        assert len(out.artifacts) == 2
    finally:
        register(TrivyScanner())  # restore default


def test_image_scan_high_warns(monkeypatch):
    register(_FakeScanner("trivy", VulnerabilityCounts(high=3)))
    try:
        ctx = _ctx_with_images(monkeypatch, ["img:a"], {"failOnCritical": True, "warnOnHigh": True})
        out = image_scan.run(ctx)
        assert out.status == ValidationStepStatus.warning
        assert out.severity == ValidationSeverity.high
    finally:
        register(TrivyScanner())


def test_image_scan_clean_passes(monkeypatch):
    register(_FakeScanner("trivy", VulnerabilityCounts()))
    try:
        ctx = _ctx_with_images(monkeypatch, ["img:a", "img:b"], {})
        out = image_scan.run(ctx)
        assert out.status == ValidationStepStatus.passed
        assert out.severity == ValidationSeverity.none
    finally:
        register(TrivyScanner())


def test_image_scan_no_images_passes(monkeypatch):
    ctx = _ctx_with_images(monkeypatch, [], {})
    out = image_scan.run(ctx)
    assert out.status == ValidationStepStatus.passed
    assert "No container images" in out.summary


def test_image_scan_unknown_scanner_errors(monkeypatch):
    ctx = _ctx_with_images(monkeypatch, ["img:a"], {"scanner": "does-not-exist"})
    out = image_scan.run(ctx)
    assert out.status == ValidationStepStatus.error


def test_image_scan_critical_but_policy_off_passes(monkeypatch):
    register(_FakeScanner("trivy", VulnerabilityCounts(critical=1)))
    try:
        ctx = _ctx_with_images(monkeypatch, ["img:a"], {"failOnCritical": False, "warnOnHigh": False})
        out = image_scan.run(ctx)
        assert out.status == ValidationStepStatus.passed
    finally:
        register(TrivyScanner())


# ---------------------------------------------------------------------------
# custom.kubernetes_job pure helpers
# ---------------------------------------------------------------------------


def test_job_name_is_dns1123():
    name = kubernetes_job.job_name(12, "Company_Policy Check!")
    assert name == "foyre-val-12-company-policy-check"
    assert len(name) <= 63


def test_build_job_manifest_is_hardened():
    m = kubernetes_job.build_job_manifest(
        name="j",
        namespace="foyre-validation",
        image="registry.example.com/checker:latest",
        command=["/app/check"],
        args=["--input", "/foyre/input/workload-inventory.json"],
        env={"FOO": "bar"},
        configmap_name="j-input",
        timeout_seconds=300,
    )
    spec = m["spec"]["template"]["spec"]
    assert spec["automountServiceAccountToken"] is False
    assert spec["hostNetwork"] is False
    assert spec["hostPID"] is False
    assert spec["restartPolicy"] == "Never"
    assert m["spec"]["backoffLimit"] == 0
    assert m["spec"]["activeDeadlineSeconds"] == 300

    container = spec["containers"][0]
    sc = container["securityContext"]
    assert sc["allowPrivilegeEscalation"] is False
    assert sc["privileged"] is False
    assert sc["capabilities"]["drop"] == ["ALL"]
    assert container["command"] == ["/app/check"]
    assert container["env"] == [{"name": "FOO", "value": "bar"}]
    # No way for an admin to inject host mounts: the only volumes are the
    # input configMap and an emptyDir output.
    vol_types = {list(v.keys())[1] for v in spec["volumes"]}  # second key after 'name'
    assert vol_types == {"configMap", "emptyDir"}


def test_build_input_configmap():
    cm = kubernetes_job.build_input_configmap("j-input", "ns", {"a.json": "{}"})
    assert cm["kind"] == "ConfigMap"
    assert cm["data"]["a.json"] == "{}"


def test_parse_result_from_logs_whole():
    logs = '{"status": "passed", "summary": "ok"}'
    assert kubernetes_job.parse_result_from_logs(logs) == {"status": "passed", "summary": "ok"}


def test_parse_result_from_logs_with_noise():
    logs = "starting checks...\nrunning\n" + '{"status": "failed", "severity": "high"}\n' + "done\n"
    res = kubernetes_job.parse_result_from_logs(logs)
    assert res == {"status": "failed", "severity": "high"}


def test_parse_result_from_logs_picks_last_object():
    logs = '{"status":"passed"}\n{"status":"warning"}\n'
    res = kubernetes_job.parse_result_from_logs(logs)
    assert res["status"] == "warning"


def test_parse_result_from_logs_none_when_no_json():
    assert kubernetes_job.parse_result_from_logs("no json here") is None
    assert kubernetes_job.parse_result_from_logs("") is None


def test_normalize_result_maps_fields():
    status, sev, summary, findings = kubernetes_job.normalize_result(
        {"status": "warning", "severity": "medium", "summary": "s", "findings": [{"x": 1}]}
    )
    assert status == ValidationStepStatus.warning
    assert sev == ValidationSeverity.medium
    assert summary == "s"
    assert findings == [{"x": 1}]


def test_normalize_result_bad_values_default_to_error_none():
    status, sev, summary, findings = kubernetes_job.normalize_result(
        {"status": "explode", "severity": "spicy", "findings": "nope"}
    )
    assert status == ValidationStepStatus.error
    assert sev == ValidationSeverity.none
    assert findings == []
