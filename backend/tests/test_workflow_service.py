"""Unit tests for request status transitions."""

from __future__ import annotations

import pytest

from app.domain.enums import RequestStatus, Role
from app.services import workflow_service


def test_requester_draft_to_submitted() -> None:
    workflow_service.assert_transition(
        RequestStatus.draft, Role.requester, RequestStatus.submitted
    )


def test_requester_cannot_skip_to_approved() -> None:
    with pytest.raises(workflow_service.TransitionNotAllowed):
        workflow_service.assert_transition(
            RequestStatus.draft, Role.requester, RequestStatus.approved
        )


def test_reviewer_submitted_to_under_review() -> None:
    workflow_service.assert_transition(
        RequestStatus.submitted, Role.reviewer, RequestStatus.under_review
    )


def test_reviewer_ready_for_review_to_approved() -> None:
    workflow_service.assert_transition(
        RequestStatus.ready_for_review, Role.reviewer, RequestStatus.approved
    )


def test_requester_ready_for_review_back_to_submitted() -> None:
    workflow_service.assert_transition(
        RequestStatus.ready_for_review, Role.requester, RequestStatus.submitted
    )
