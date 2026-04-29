"""Deterministic risk classification.

A pure function operating on a validated `IntakePayload`. Rules are plain
Python if-statements — no DSL, no policy engine. To add a rule, append
another `if … bump(...)` block below with a clear reason string.

Design rules:
  - Rules only escalate level; they never lower it. Each rule contributes a
    candidate level; the final level is the max across all triggered rules.
  - Rules also contribute human-readable reasons that are kept in the order
    they fire, so a reviewer can see *why* a request got its level.
  - If any critical input is "unknown", the whole request is `unknown` — a
    classification the reviewer must resolve by asking follow-up questions.
"""
from __future__ import annotations

from app.domain.enums import DataClassification, RiskLevel, YesNoUnknown
from app.schemas.request import IntakePayload

# Ordered from least to most severe. `unknown` is a separate classification
# and deliberately not part of this ordering.
_ESCALATION_ORDER: tuple[RiskLevel, ...] = (
    RiskLevel.low,
    RiskLevel.medium,
    RiskLevel.high,
)


def _escalate(current: RiskLevel, candidate: RiskLevel) -> RiskLevel:
    """Return the higher of two ordered risk levels."""
    return max((current, candidate), key=_ESCALATION_ORDER.index)


def derive_risk(payload: IntakePayload) -> tuple[RiskLevel, list[str]]:
    """Classify the intake request and return (level, reasons)."""
    # Short-circuit: if the requester said they *don't know* whether sensitive
    # data is involved, we cannot make an honest low/medium/high call.
    if payload.handles_sensitive_data == YesNoUnknown.unknown:
        return RiskLevel.unknown, ["Sensitive data handling is unknown"]

    level = RiskLevel.low
    reasons: list[str] = []

    def bump(to: RiskLevel, reason: str) -> None:
        nonlocal level
        reasons.append(reason)
        level = _escalate(level, to)

    # --- HIGH ---------------------------------------------------------------
    if (
        payload.calls_external_model_api
        and payload.data_classification == DataClassification.regulated
    ):
        bump(RiskLevel.high, "External model API with regulated data")

    if payload.takes_actions:
        bump(RiskLevel.high, "Agent takes actions on behalf of a user/system")

    # --- MEDIUM -------------------------------------------------------------
    if payload.uses_enterprise_documents and payload.uses_vector_db:
        bump(RiskLevel.medium, "Enterprise documents indexed in a vector DB")

    if payload.data_classification == DataClassification.confidential:
        bump(RiskLevel.medium, "Confidential data classification")

    if (
        payload.internet_egress
        and payload.handles_sensitive_data == YesNoUnknown.yes
    ):
        bump(RiskLevel.medium, "Internet egress with sensitive data")

    # --- LOW (default) ------------------------------------------------------
    # If nothing above fired, the request stays at `low` with no reasons.
    return level, reasons
