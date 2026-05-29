"""Image scanner abstraction.

A scanner takes an image reference + step config and returns a normalized
`ScanResult` (severity counts + raw scanner output). Keeping this behind a
protocol means the image-scan step never depends on a specific scanner —
Trivy is just the bundled default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class VulnerabilityCounts:
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    unknown: int = 0

    def add(self, other: "VulnerabilityCounts") -> None:
        self.critical += other.critical
        self.high += other.high
        self.medium += other.medium
        self.low += other.low
        self.unknown += other.unknown

    def as_dict(self) -> dict[str, int]:
        return {
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "unknown": self.unknown,
        }


@dataclass
class ScanResult:
    image: str
    success: bool
    counts: VulnerabilityCounts = field(default_factory=VulnerabilityCounts)
    # Raw scanner output (e.g. Trivy JSON) to persist as an artifact.
    raw: bytes | None = None
    # MIME type for the raw artifact.
    raw_content_type: str = "application/json"
    error: str | None = None


class ImageScanner(Protocol):
    """Implemented by every scanner. `name` is the value admins put in a
    step's `config.scanner`."""

    name: str

    def scan(self, image: str, config: dict[str, Any]) -> ScanResult:
        ...
