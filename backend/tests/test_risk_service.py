"""Unit tests for deterministic risk classification."""

from __future__ import annotations

import pytest

from app.domain.enums import DataClassification, RiskLevel, YesNoUnknown
from app.schemas.request import IntakePayload
from app.services import risk_service


def test_unknown_when_sensitive_handling_unknown(minimal_intake_payload: IntakePayload) -> None:
    p = minimal_intake_payload.model_copy(
        update={"handles_sensitive_data": YesNoUnknown.unknown}
    )
    level, reasons = risk_service.derive_risk(p)
    assert level == RiskLevel.unknown
    assert "unknown" in reasons[0].lower()


def test_high_external_api_and_regulated(minimal_intake_payload: IntakePayload) -> None:
    p = minimal_intake_payload.model_copy(
        update={
            "calls_external_model_api": True,
            "data_classification": DataClassification.regulated,
        }
    )
    level, reasons = risk_service.derive_risk(p)
    assert level == RiskLevel.high
    assert any("External model API" in r for r in reasons)


def test_high_agent_actions(minimal_intake_payload: IntakePayload) -> None:
    p = minimal_intake_payload.model_copy(update={"takes_actions": True})
    level, reasons = risk_service.derive_risk(p)
    assert level == RiskLevel.high
    assert any("actions" in r.lower() for r in reasons)


def test_medium_enterprise_docs_and_vector_db(minimal_intake_payload: IntakePayload) -> None:
    p = minimal_intake_payload.model_copy(
        update={"uses_enterprise_documents": True, "uses_vector_db": True}
    )
    level, reasons = risk_service.derive_risk(p)
    assert level == RiskLevel.medium


def test_low_internal_no_triggers(minimal_intake_payload: IntakePayload) -> None:
    level, reasons = risk_service.derive_risk(minimal_intake_payload)
    assert level == RiskLevel.low
    assert reasons == []
