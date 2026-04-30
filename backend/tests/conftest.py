"""Shared fixtures for backend tests."""

from __future__ import annotations

import pytest

from app.domain.enums import DataClassification, Environment, WorkloadType, YesNoUnknown
from app.schemas.request import IntakePayload


@pytest.fixture
def minimal_intake_payload() -> IntakePayload:
    """A valid baseline payload; override fields in individual tests."""

    return IntakePayload(
        application_name="Test App",
        business_owner="Owner",
        technical_owner="Tech",
        team="platform",
        description="Unit test fixture",
        environment=Environment.dev,
        workload_type=WorkloadType.chatbot,
        handles_sensitive_data=YesNoUnknown.no,
        data_classification=DataClassification.internal,
    )
