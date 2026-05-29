"""Trivy image scanner (the bundled default).

Shells out to the `trivy` CLI (bundled in the Foyre runtime image) and
normalizes its JSON output into severity counts. The JSON parsing is a
pure staticmethod so it's testable without the binary present.

If the `trivy` binary is missing, `scan()` returns an unsuccessful
ScanResult with a clear error rather than raising — the image-scan step
turns that into a step error so operators see exactly what's wrong.
"""
from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

from app.validation.scanners.base import ScanResult, VulnerabilityCounts

logger = logging.getLogger(__name__)

# Hard cap so one slow image can't run forever; the step-level timeout in
# the runner wraps this as well.
_SCAN_TIMEOUT_SECONDS = 600


class TrivyScanner:
    name = "trivy"

    def scan(self, image: str, config: dict[str, Any]) -> ScanResult:
        cmd = [
            "trivy",
            "image",
            "--format",
            "json",
            "--quiet",
            "--no-progress",
            "--severity",
            "CRITICAL,HIGH,MEDIUM,LOW,UNKNOWN",
        ]
        if config.get("ignoreUnfixed"):
            cmd.append("--ignore-unfixed")
        cmd.append(image)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=False,  # keep bytes for the raw artifact
                timeout=_SCAN_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError:
            return ScanResult(
                image=image,
                success=False,
                error="`trivy` CLI not found on PATH. It is bundled in the Foyre image; install it for local runs.",
            )
        except subprocess.TimeoutExpired:
            return ScanResult(
                image=image,
                success=False,
                error=f"trivy timed out after {_SCAN_TIMEOUT_SECONDS}s scanning {image}",
            )

        if proc.returncode != 0:
            stderr = (proc.stderr or b"").decode("utf-8", "replace").strip()
            logger.warning("trivy failed for %s rc=%s: %s", image, proc.returncode, stderr)
            return ScanResult(
                image=image,
                success=False,
                error=f"trivy exited {proc.returncode}: {stderr[:500]}",
            )

        raw = proc.stdout or b"{}"
        try:
            counts = self.parse(raw)
        except (ValueError, KeyError) as e:
            return ScanResult(
                image=image,
                success=False,
                raw=raw,
                error=f"could not parse trivy output: {e}",
            )
        return ScanResult(image=image, success=True, counts=counts, raw=raw)

    @staticmethod
    def parse(raw: bytes) -> VulnerabilityCounts:
        """Count vulnerabilities by severity from Trivy JSON output."""
        doc = json.loads(raw.decode("utf-8"))
        counts = VulnerabilityCounts()
        for result in doc.get("Results", []) or []:
            for vuln in result.get("Vulnerabilities", []) or []:
                sev = (vuln.get("Severity") or "UNKNOWN").upper()
                if sev == "CRITICAL":
                    counts.critical += 1
                elif sev == "HIGH":
                    counts.high += 1
                elif sev == "MEDIUM":
                    counts.medium += 1
                elif sev == "LOW":
                    counts.low += 1
                else:
                    counts.unknown += 1
        return counts
