"""Result resolution for script/container validation steps.

Turns a finished step's raw signals — exit code, container terminated
reason, stdout, and an optional `result.json` — into a normalized
`StepOutcome`, applying the precedence defined in
docs/dev/validation-extensibility-design.md §5.2:

  1. `result.json` (richest)        → normalized result
  2. a single JSON object on stdout → normalized result (back-compat)
  3. exit code                      → simple status

Exit-code mapping (when no JSON result is provided):
  - 0                         → passed
  - 2                         → warning
  - other "clean" nonzero     → failed   (ran, workload failed the check)
  - timeout / OOMKill / etc.  → error    (the check couldn't run)

This module is pure and unit-tested; the executors supply the raw signals.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import ValidationSeverity, ValidationStepStatus

_VALID_STATUS = {s.value for s in ValidationStepStatus}
_VALID_SEVERITY = {s.value for s in ValidationSeverity}

# Exit-code conventions for the "no JSON result" path.
EXIT_PASSED = 0
EXIT_WARNING = 2

# Container terminated reasons that mean "couldn't run" rather than
# "ran and failed". 137 is SIGKILL (commonly OOM).
_INFRA_FAILURE_REASONS = {"OOMKilled", "DeadlineExceeded", "Error"}
_INFRA_FAILURE_EXIT_CODES = {137}


@dataclass
class ResolvedResult:
    status: ValidationStepStatus
    severity: ValidationSeverity = ValidationSeverity.none
    summary: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)
    error_message: str | None = None
    # The parsed result dict, when one was used (so the caller can persist
    # it as a `result.json`/`custom-result.json` artifact).
    result_obj: dict[str, Any] | None = None
    # How the result was derived: "result.json" | "stdout" | "exit_code".
    source: str = "exit_code"


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Return the last well-formed top-level JSON object in `text`.

    Tries the whole string first, then scans backward for the last balanced
    `{...}` block so log noise before the result is tolerated.
    """
    text = (text or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except ValueError:
        pass
    end = text.rfind("}")
    while end != -1:
        depth = 0
        start = -1
        for i in range(end, -1, -1):
            ch = text[i]
            if ch == "}":
                depth += 1
            elif ch == "{":
                depth -= 1
                if depth == 0:
                    start = i
                    break
        if start != -1:
            candidate = text[start : end + 1]
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except ValueError:
                pass
            end = text.rfind("}", 0, start)
        else:
            break
    return None


def _safe_json_bytes(data: bytes | None) -> dict[str, Any] | None:
    if not data:
        return None
    try:
        obj = json.loads(data.decode("utf-8"))
        return obj if isinstance(obj, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# Normalize an explicit result dict
# ---------------------------------------------------------------------------


def normalize_result_dict(
    result: dict[str, Any],
) -> tuple[ValidationStepStatus, ValidationSeverity, str, list[dict[str, Any]]]:
    """Coerce a custom result dict into typed outcome fields.

    A `status` that isn't recognized maps to `error` (the step claimed a
    result we can't interpret). Severity defaults to `none`; non-list
    findings are dropped.
    """
    status_str = str(result.get("status", "")).lower()
    status = (
        ValidationStepStatus(status_str)
        if status_str in _VALID_STATUS
        else ValidationStepStatus.error
    )
    sev_str = str(result.get("severity", "none")).lower()
    severity = (
        ValidationSeverity(sev_str) if sev_str in _VALID_SEVERITY else ValidationSeverity.none
    )
    summary = str(result.get("summary") or "")
    findings = result.get("findings") or []
    if not isinstance(findings, list):
        findings = []
    return status, severity, summary, findings


def _from_result_obj(obj: dict[str, Any], source: str) -> ResolvedResult:
    status, severity, summary, findings = normalize_result_dict(obj)
    return ResolvedResult(
        status=status,
        severity=severity,
        summary=summary,
        findings=findings,
        result_obj=obj,
        source=source,
    )


# ---------------------------------------------------------------------------
# Precedence resolution
# ---------------------------------------------------------------------------


def resolve_outcome(
    *,
    job_state: str,
    exit_code: int | None,
    terminated_reason: str | None = None,
    stdout: str = "",
    result_json_bytes: bytes | None = None,
) -> ResolvedResult:
    """Apply the precedence (result.json → stdout JSON → exit code).

    `job_state` is the runner's coarse view: "succeeded" | "failed" |
    "timeout". `exit_code` / `terminated_reason` come from the main
    container's terminated state when available.
    """
    # 1. result.json
    obj = _safe_json_bytes(result_json_bytes)
    if obj is not None:
        return _from_result_obj(obj, source="result.json")

    # 2. stdout JSON (back-compat with the original contract)
    obj = extract_json_object(stdout)
    if obj is not None:
        return _from_result_obj(obj, source="stdout")

    # 3. exit code / job state
    if job_state == "timeout":
        return ResolvedResult(
            status=ValidationStepStatus.error,
            summary="Step timed out.",
            error_message="timed out",
        )
    if terminated_reason in _INFRA_FAILURE_REASONS or exit_code in _INFRA_FAILURE_EXIT_CODES:
        detail = terminated_reason or f"exit {exit_code}"
        return ResolvedResult(
            status=ValidationStepStatus.error,
            summary=f"Step could not run ({detail}).",
            error_message=f"container terminated: {detail}",
        )

    if exit_code is None:
        # Couldn't read the container exit code; fall back to job state.
        if job_state == "succeeded":
            return ResolvedResult(status=ValidationStepStatus.passed, summary="Step passed.")
        return ResolvedResult(
            status=ValidationStepStatus.failed,
            summary="Step failed.",
            error_message="job did not succeed and emitted no result",
        )

    if exit_code == EXIT_PASSED:
        return ResolvedResult(status=ValidationStepStatus.passed, summary="Step passed.")
    if exit_code == EXIT_WARNING:
        return ResolvedResult(
            status=ValidationStepStatus.warning,
            severity=ValidationSeverity.medium,
            summary="Step reported a warning (exit 2).",
        )
    return ResolvedResult(
        status=ValidationStepStatus.failed,
        summary=f"Step failed (exit {exit_code}).",
        error_message=f"non-zero exit code {exit_code}",
    )
