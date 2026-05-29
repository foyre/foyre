"""Value objects + status math shared by the runner and step executors.

Executors are pure-ish: they receive a `StepContext` and return a
`StepOutcome`. The runner is responsible for persisting outcomes to the
DB (step results + artifacts) and for aggregating per-step outcomes into
a run-level status and approval impact. Keeping the combination logic
here (rather than in the runner) makes it independently testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.domain.enums import (
    ApprovalImpact,
    FailurePolicy,
    ValidationRunStatus,
    ValidationSeverity,
    ValidationStepStatus,
)


@dataclass
class ArtifactDraft:
    """An artifact an executor wants persisted. The runner turns these
    into `ValidationArtifact` rows."""

    name: str
    artifact_type: str  # json | yaml | text | log | sarif | sbom | scan_result
    content: bytes
    content_type: str = "application/json"


@dataclass
class StepOutcome:
    """Normalized result of executing one step."""

    status: ValidationStepStatus
    severity: ValidationSeverity = ValidationSeverity.none
    summary: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    artifacts: list[ArtifactDraft] = field(default_factory=list)
    error_message: str | None = None


@dataclass
class StepContext:
    """Everything an executor needs to do its job.

    `upstream` holds the outcomes of already-completed steps in this run,
    keyed by step name, so a step can consume an earlier step's results
    (e.g. kubernetes_security reading workload_inventory's findings).
    """

    run_id: int
    step: dict[str, Any]  # normalized step definition from the pipeline
    kubeconfig_yaml: str
    upstream: dict[str, "StepOutcome"] = field(default_factory=dict)

    @property
    def config(self) -> dict[str, Any]:
        return self.step.get("config") or {}

    @property
    def step_name(self) -> str:
        return self.step["name"]

    @property
    def step_type(self) -> str:
        return self.step["type"]

    def upstream_of_type(self, step_type: str) -> "StepOutcome | None":
        """Return the first completed upstream outcome of a given step type."""
        for name in self.step.get("dependsOn", []):
            out = self.upstream.get(name)
            if out is not None and self.upstream_type_map.get(name) == step_type:
                return out
        # Fall back to scanning all upstream outcomes (not just declared deps).
        for name, out in self.upstream.items():
            if self.upstream_type_map.get(name) == step_type:
                return out
        return None

    # Populated by the runner before each step so `upstream_of_type` can
    # resolve a step name back to its type.
    upstream_type_map: dict[str, str] = field(default_factory=dict)


# Type alias for the executor callable contract.
ExecutorFn = Callable[[StepContext], StepOutcome]


# ---------------------------------------------------------------------------
# Status aggregation
# ---------------------------------------------------------------------------

# Ordering used to take the "worst" value across steps.
_RUN_ORDER: tuple[ValidationRunStatus, ...] = (
    ValidationRunStatus.passed,
    ValidationRunStatus.warning,
    ValidationRunStatus.failed,
)
_IMPACT_ORDER: tuple[ApprovalImpact, ...] = (
    ApprovalImpact.none,
    ApprovalImpact.warning,
    ApprovalImpact.blocked,
)


def _worse_run(a: ValidationRunStatus, b: ValidationRunStatus) -> ValidationRunStatus:
    return max((a, b), key=_RUN_ORDER.index)


def _worse_impact(a: ApprovalImpact, b: ApprovalImpact) -> ApprovalImpact:
    return max((a, b), key=_IMPACT_ORDER.index)


@dataclass
class StepRollupInput:
    """Minimal projection of a step result the aggregator needs."""

    status: ValidationStepStatus
    failure_policy: FailurePolicy


def aggregate_run(steps: list[StepRollupInput]) -> tuple[ValidationRunStatus, ApprovalImpact]:
    """Combine per-step (status, failure_policy) into (run_status, impact).

    Rules:
      - passed / skipped steps never downgrade anything.
      - failure_policy `ignore` means a step never affects run status or
        approval impact, regardless of its result.
      - A failed/error step with policy `block` → run failed + approval
        blocked.
      - A failed/error step with policy `warn`, or any `warning` step with
        policy `warn`/`block` → run at least `warning`, approval at least
        `warning`.

    A run with no contributing steps is `passed` / `none`.
    """
    run = ValidationRunStatus.passed
    impact = ApprovalImpact.none

    bad_statuses = {ValidationStepStatus.failed, ValidationStepStatus.error}

    for s in steps:
        if s.status in (ValidationStepStatus.passed, ValidationStepStatus.skipped, ValidationStepStatus.queued, ValidationStepStatus.running):
            continue
        if s.failure_policy == FailurePolicy.ignore:
            continue
        if s.status in bad_statuses:
            if s.failure_policy == FailurePolicy.block:
                run = _worse_run(run, ValidationRunStatus.failed)
                impact = _worse_impact(impact, ApprovalImpact.blocked)
            else:  # warn
                run = _worse_run(run, ValidationRunStatus.warning)
                impact = _worse_impact(impact, ApprovalImpact.warning)
        elif s.status == ValidationStepStatus.warning:
            run = _worse_run(run, ValidationRunStatus.warning)
            impact = _worse_impact(impact, ApprovalImpact.warning)

    return run, impact
