"""builtin.workload_inventory executor.

Connects to the validation environment's vcluster, enumerates deployed
resources (no secret values), and emits:
  - a `details` summary (counts + discovered images + light security
    rollup) the UI can show without parsing artifacts;
  - a full `workload-inventory.json` artifact downstream steps consume
    and reviewers can download.
"""
from __future__ import annotations

import json

from app.validation import kube
from app.validation.inventory import collect_inventory
from app.domain.enums import ValidationSeverity, ValidationStepStatus
from app.validation.types import ArtifactDraft, StepContext, StepOutcome

INVENTORY_ARTIFACT_NAME = "workload-inventory.json"


def run(ctx: StepContext) -> StepOutcome:
    api = kube.api_client_from_kubeconfig(ctx.kubeconfig_yaml)
    inv = collect_inventory(api, ctx.config)

    counts = inv.get("counts", {})
    images = inv.get("images", [])
    summary = (
        f"Discovered {len(inv.get('workloads', []))} workloads, "
        f"{counts.get('pods', 0)} pods, and {len(images)} unique container images."
    )

    # Lean details for the UI; the full inventory lives in the artifact so
    # we don't store the (potentially large) workloads list twice.
    details = {
        "namespaces": inv.get("namespaces", []),
        "counts": counts,
        "images": images,
        "security": inv.get("security", {}),
    }

    artifact = ArtifactDraft(
        name=INVENTORY_ARTIFACT_NAME,
        artifact_type="json",
        content=json.dumps(inv, indent=2, default=str).encode("utf-8"),
        content_type="application/json",
    )

    return StepOutcome(
        status=ValidationStepStatus.passed,
        severity=ValidationSeverity.none,
        summary=summary,
        details=details,
        artifacts=[artifact],
    )
