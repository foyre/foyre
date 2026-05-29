"""Pluggable container image scanner registry.

Foyre ships with Trivy as the default scanner but is deliberately NOT
hard-wired to it. A scanner is anything implementing the `ImageScanner`
protocol (see `base.py`); operators / contributors can register
additional scanners (Grype, NeuVector, an external service) without
touching the image-scan step executor.

The default `trivy` scanner is registered on import.
"""
from __future__ import annotations

from app.validation.scanners.base import (
    ImageScanner,
    ScanResult,
    VulnerabilityCounts,
)
from app.validation.scanners.trivy import TrivyScanner

_REGISTRY: dict[str, ImageScanner] = {}


def register(scanner: ImageScanner) -> None:
    """Register (or override) a scanner under its `name`."""
    _REGISTRY[scanner.name] = scanner


def get_scanner(name: str) -> ImageScanner | None:
    return _REGISTRY.get(name)


def registered_names() -> list[str]:
    return sorted(_REGISTRY)


# Register the bundled default.
register(TrivyScanner())

__all__ = [
    "ImageScanner",
    "ScanResult",
    "VulnerabilityCounts",
    "TrivyScanner",
    "register",
    "get_scanner",
    "registered_names",
]
