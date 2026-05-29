"""builtin.image_scan executor.

Scans the unique container images discovered by the workload inventory
using a pluggable scanner (default: Trivy). Severity counts are
aggregated; raw scanner output is attached as one artifact per image.

Status mapping (configurable):
  - critical vulns + failOnCritical (default True) → failed
  - high vulns + warnOnHigh (default True)         → warning
  - a scanner error on any image (and nothing worse) → error
  - otherwise                                       → passed
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.domain.enums import ValidationSeverity, ValidationStepStatus
from app.validation import kube
from app.validation.executors.workload_inventory import INVENTORY_ARTIFACT_NAME
from app.validation.inventory import collect_inventory
from app.validation.scanners import get_scanner
from app.validation.scanners.base import VulnerabilityCounts
from app.validation.types import ArtifactDraft, StepContext, StepOutcome

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_.-]+")


def _images_from_upstream(ctx: StepContext) -> list[str] | None:
    inv_outcome = ctx.upstream_of_type("builtin.workload_inventory")
    if inv_outcome is None:
        return None
    # Prefer the lean details (already has the image list). An explicit
    # empty list is a valid answer ("no images"), distinct from absence.
    images = inv_outcome.details.get("images")
    if images is not None:
        return list(images)
    for art in inv_outcome.artifacts:
        if art.name == INVENTORY_ARTIFACT_NAME:
            try:
                return json.loads(art.content.decode("utf-8")).get("images")
            except (ValueError, UnicodeDecodeError):
                return None
    return None


def _safe_filename(image: str) -> str:
    return _SAFE_NAME.sub("_", image).strip("_") or "image"


def run(ctx: StepContext) -> StepOutcome:
    images = _images_from_upstream(ctx)
    if images is None:
        api = kube.api_client_from_kubeconfig(ctx.kubeconfig_yaml)
        images = collect_inventory(api, {}).get("images", [])

    images = sorted(set(images))
    if not images:
        return StepOutcome(
            status=ValidationStepStatus.passed,
            severity=ValidationSeverity.none,
            summary="No container images discovered to scan.",
            details={"images": [], "counts": VulnerabilityCounts().as_dict()},
        )

    scanner_name = ctx.config.get("scanner", "trivy")
    scanner = get_scanner(scanner_name)
    if scanner is None:
        return StepOutcome(
            status=ValidationStepStatus.error,
            summary=f"Unknown image scanner '{scanner_name}'.",
            error_message=f"no scanner registered under '{scanner_name}'",
        )

    fail_on_critical = ctx.config.get("failOnCritical", True)
    warn_on_high = ctx.config.get("warnOnHigh", True)

    total = VulnerabilityCounts()
    per_image: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    artifacts: list[ArtifactDraft] = []
    any_error = False

    for image in images:
        res = scanner.scan(image, ctx.config)
        if not res.success:
            any_error = True
            per_image.append({"image": image, "error": res.error})
            continue
        total.add(res.counts)
        per_image.append({"image": image, "counts": res.counts.as_dict()})
        if res.raw:
            artifacts.append(
                ArtifactDraft(
                    name=f"scan-{_safe_filename(image)}.json",
                    artifact_type="scan_result",
                    content=res.raw,
                    content_type=res.raw_content_type,
                )
            )
        if res.counts.critical or res.counts.high:
            sev = "critical" if res.counts.critical else "high"
            findings.append(
                {
                    "severity": sev,
                    "title": "Vulnerable container image",
                    "resource": image,
                    "message": (
                        f"{res.counts.critical} critical, {res.counts.high} high, "
                        f"{res.counts.medium} medium vulnerabilities found."
                    ),
                    "recommendation": "Rebuild on a patched base image or upgrade affected packages.",
                }
            )

    # Determine status + severity.
    if total.critical and fail_on_critical:
        status, severity = ValidationStepStatus.failed, ValidationSeverity.critical
    elif total.high and warn_on_high:
        status, severity = ValidationStepStatus.warning, ValidationSeverity.high
    elif any_error:
        status, severity = ValidationStepStatus.error, ValidationSeverity.none
    elif total.critical or total.high:
        # Vulnerabilities present but policy says don't fail/warn on them.
        status, severity = ValidationStepStatus.passed, ValidationSeverity.medium
    else:
        status, severity = ValidationStepStatus.passed, ValidationSeverity.none

    summary = (
        f"Scanned {len(images)} image(s): {total.critical} critical, "
        f"{total.high} high, {total.medium} medium."
    )
    if any_error:
        summary += " Some images could not be scanned."

    details = {
        "scanner": scanner_name,
        "counts": total.as_dict(),
        "images": per_image,
    }

    # A run-level summary artifact for easy download.
    artifacts.append(
        ArtifactDraft(
            name="image-scan-summary.json",
            artifact_type="json",
            content=json.dumps(details, indent=2).encode("utf-8"),
            content_type="application/json",
        )
    )

    return StepOutcome(
        status=status,
        severity=severity,
        summary=summary,
        findings=findings,
        details=details,
        artifacts=artifacts,
        error_message=None,
    )
