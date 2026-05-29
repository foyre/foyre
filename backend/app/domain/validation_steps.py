"""Registry of known validation step types.

This is the single source of truth for "which step `type` strings are
valid in a pipeline definition". The pipeline parser validates against
this registry; the runner (chunk 3+) dispatches executors keyed on the
same strings.

Design intent: adding a new step type is a one-line addition here plus an
executor registration in the runner. The brief lists several *future*
types — they're intentionally NOT registered yet, so a pipeline that
references them fails validation with a clear message rather than
silently accepting a step nothing can run.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StepTypeSpec:
    """Static metadata describing a step type.

    `builtin` distinguishes Foyre-provided checks from user-supplied
    containerized steps. `custom_job` flags the type that creates a
    Kubernetes Job from an admin-provided image (extra guardrails apply
    in later chunks).
    """

    type: str
    display_name: str
    description: str
    builtin: bool
    custom_job: bool = False


# MVP step types. Keep keys stable — they're persisted in pipeline
# definitions and run snapshots.
SUPPORTED_STEP_TYPES: dict[str, StepTypeSpec] = {
    "builtin.workload_inventory": StepTypeSpec(
        type="builtin.workload_inventory",
        display_name="Workload Inventory",
        description=(
            "Enumerate Kubernetes resources deployed in the validation "
            "environment and collect non-secret metadata (images, "
            "securityContext, resource limits, volume types)."
        ),
        builtin=True,
    ),
    "builtin.kubernetes_security": StepTypeSpec(
        type="builtin.kubernetes_security",
        display_name="Kubernetes Security Review",
        description=(
            "Inspect the workload inventory for risky configuration: "
            "privileged containers, hostPath/hostNetwork usage, missing "
            "resource limits, root execution, and risky capabilities."
        ),
        builtin=True,
    ),
    "builtin.image_scan": StepTypeSpec(
        type="builtin.image_scan",
        display_name="Container Image Scan",
        description=(
            "Scan unique container images discovered by the inventory for "
            "known vulnerabilities. Defaults to Trivy; the scanner is "
            "pluggable."
        ),
        builtin=True,
    ),
    "custom.kubernetes_job": StepTypeSpec(
        type="custom.kubernetes_job",
        display_name="Custom Kubernetes Job",
        description=(
            "Run an admin-provided container image as a Kubernetes Job "
            "inside the validation environment and ingest its normalized "
            "JSON result. Lets teams bring their own validation logic."
        ),
        builtin=False,
        custom_job=True,
    ),
}


def is_supported(step_type: str) -> bool:
    return step_type in SUPPORTED_STEP_TYPES


def get_spec(step_type: str) -> StepTypeSpec | None:
    return SUPPORTED_STEP_TYPES.get(step_type)


# Future step types the product intends to add. Listed for documentation
# and so the parser can give a "planned, not yet available" hint instead
# of a generic "unknown type" error.
PLANNED_STEP_TYPES: frozenset[str] = frozenset(
    {
        "custom.webhook",
        "custom.script",
        "builtin.network_egress",
        "builtin.policy_engine",
        "builtin.sbom",
        "neuvector.scan",
        "trivy.scan",
        "grype.scan",
        "kyverno.audit",
        "opa.gatekeeper",
    }
)
