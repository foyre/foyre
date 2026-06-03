"""Tests for result resolution + precedence (the relaxed step contract)."""

from __future__ import annotations

import json

from app.domain.enums import ValidationSeverity, ValidationStepStatus
from app.validation import results


# ---------------------------------------------------------------------------
# extract_json_object
# ---------------------------------------------------------------------------


def test_extract_whole():
    assert results.extract_json_object('{"status": "passed"}') == {"status": "passed"}


def test_extract_with_noise():
    logs = "starting\nworking...\n" + '{"status":"failed"}\n' + "bye\n"
    assert results.extract_json_object(logs) == {"status": "failed"}


def test_extract_last_object_wins():
    assert results.extract_json_object('{"a":1}\n{"b":2}\n')["b"] == 2


def test_extract_none():
    assert results.extract_json_object("no json") is None
    assert results.extract_json_object("") is None


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------


def test_result_json_wins_over_everything():
    r = results.resolve_outcome(
        job_state="failed",
        exit_code=1,
        stdout='{"status": "warning"}',
        result_json_bytes=json.dumps({"status": "passed", "summary": "ok"}).encode(),
    )
    assert r.status == ValidationStepStatus.passed
    assert r.source == "result.json"
    assert r.result_obj == {"status": "passed", "summary": "ok"}


def test_stdout_json_used_when_no_result_file():
    r = results.resolve_outcome(
        job_state="failed",
        exit_code=1,
        stdout='{"status": "warning", "severity": "medium"}',
    )
    assert r.status == ValidationStepStatus.warning
    assert r.severity == ValidationSeverity.medium
    assert r.source == "stdout"


def test_exit_zero_no_json_passes():
    # The relaxed contract: a plain container that exits 0 now passes
    # (previously this errored for lack of JSON).
    r = results.resolve_outcome(job_state="succeeded", exit_code=0, stdout="done, all good")
    assert r.status == ValidationStepStatus.passed
    assert r.source == "exit_code"


def test_exit_two_is_warning():
    r = results.resolve_outcome(job_state="failed", exit_code=2, stdout="heads up")
    assert r.status == ValidationStepStatus.warning


def test_clean_nonzero_is_failed():
    r = results.resolve_outcome(job_state="failed", exit_code=1, stdout="nope")
    assert r.status == ValidationStepStatus.failed
    assert r.error_message


# ---------------------------------------------------------------------------
# error vs failed
# ---------------------------------------------------------------------------


def test_timeout_is_error_not_failed():
    r = results.resolve_outcome(job_state="timeout", exit_code=None, stdout="")
    assert r.status == ValidationStepStatus.error
    assert "timed out" in (r.error_message or "")


def test_oomkilled_is_error():
    r = results.resolve_outcome(
        job_state="failed", exit_code=137, terminated_reason="OOMKilled", stdout=""
    )
    assert r.status == ValidationStepStatus.error


def test_exit_137_is_error_even_without_reason():
    r = results.resolve_outcome(job_state="failed", exit_code=137, stdout="")
    assert r.status == ValidationStepStatus.error


def test_unknown_exit_with_no_code_falls_back_to_job_state():
    assert (
        results.resolve_outcome(job_state="succeeded", exit_code=None, stdout="").status
        == ValidationStepStatus.passed
    )
    assert (
        results.resolve_outcome(job_state="failed", exit_code=None, stdout="").status
        == ValidationStepStatus.failed
    )


# ---------------------------------------------------------------------------
# normalize_result_dict
# ---------------------------------------------------------------------------


def test_normalize_maps_fields():
    status, sev, summary, findings = results.normalize_result_dict(
        {"status": "warning", "severity": "high", "summary": "s", "findings": [{"x": 1}]}
    )
    assert status == ValidationStepStatus.warning
    assert sev == ValidationSeverity.high
    assert summary == "s"
    assert findings == [{"x": 1}]


def test_normalize_bad_values_default():
    status, sev, summary, findings = results.normalize_result_dict(
        {"status": "explode", "severity": "spicy", "findings": "nope"}
    )
    assert status == ValidationStepStatus.error
    assert sev == ValidationSeverity.none
    assert findings == []


# ---------------------------------------------------------------------------
# Back-compat delegators still importable from kubernetes_job
# ---------------------------------------------------------------------------


def test_kubernetes_job_backcompat_shims():
    from app.validation.executors import kubernetes_job

    assert kubernetes_job.parse_result_from_logs('{"status":"passed"}') == {"status": "passed"}
    status, *_ = kubernetes_job.normalize_result({"status": "failed"})
    assert status == ValidationStepStatus.failed
