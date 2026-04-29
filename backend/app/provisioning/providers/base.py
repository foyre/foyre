"""Provisioning provider interface.

Concrete providers live beside this file:
  - vcluster.py   : vcluster-based virtual cluster (default)

Future providers (namespace-only, K3k, etc.) drop in as siblings implementing
the same protocol.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.request import IntakeRequest


@dataclass
class ProvisioningResult:
    provider: str
    target_ref: str
    detail: dict | None = None


class ProvisioningProvider(Protocol):
    """Minimal provider interface; deliberately tiny. Add new verbs when a
    real provider needs them.
    """

    name: str

    def provision(self, req: IntakeRequest) -> ProvisioningResult: ...
