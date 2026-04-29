"""Request status workflow.

All status transitions go through `assert_transition()`. The allowed-transition
table below is the *only* place the rules live. When the approval flow grows
(e.g. new `provisioning` states), extend `ALLOWED_TRANSITIONS` here.
"""
from __future__ import annotations

from app.domain.enums import PRIVILEGED_ROLES, RequestStatus, Role


def _build_transitions() -> dict[tuple[RequestStatus, Role], frozenset[RequestStatus]]:
    t: dict[tuple[RequestStatus, Role], frozenset[RequestStatus]] = {
        # Requester submits their own draft.
        (RequestStatus.draft, Role.requester): frozenset({RequestStatus.submitted}),
        # Admin can submit drafts too so a single user can exercise the full
        # workflow end-to-end for local demos.
        (RequestStatus.draft, Role.admin): frozenset({RequestStatus.submitted}),
        # Requester signals "I've deployed into my validation env, please look".
        # Also un-markable if they realize they need more time.
        (RequestStatus.submitted, Role.requester): frozenset({RequestStatus.ready_for_review}),
        (RequestStatus.ready_for_review, Role.requester): frozenset({RequestStatus.submitted}),
        (RequestStatus.submitted, Role.admin): frozenset({RequestStatus.ready_for_review}),
        (RequestStatus.ready_for_review, Role.admin): frozenset({RequestStatus.submitted}),
    }
    # Reviewer / architect / admin all get the same review-stage capabilities.
    # `ready_for_review` behaves like `submitted` from the reviewer's side.
    review_actions = frozenset(
        {RequestStatus.under_review, RequestStatus.approved, RequestStatus.rejected}
    )
    terminal_actions = frozenset({RequestStatus.approved, RequestStatus.rejected})
    for role in PRIVILEGED_ROLES:
        # `submitted` transitions stay the same; `ready_for_review` mirrors it
        # but with the role-specific set of targets merged in.
        t[(RequestStatus.submitted, role)] = t.get(
            (RequestStatus.submitted, role), frozenset()
        ) | review_actions
        t[(RequestStatus.ready_for_review, role)] = review_actions
        t[(RequestStatus.under_review, role)] = terminal_actions
    return t


# (current_status, actor_role) -> allowed target statuses.
ALLOWED_TRANSITIONS = _build_transitions()


class TransitionNotAllowed(Exception):
    pass


def assert_transition(
    current: RequestStatus, actor_role: Role, target: RequestStatus
) -> None:
    """Raise `TransitionNotAllowed` if the (current, role, target) triple
    isn't in the allow-list. This is the only enforcement point for status
    rules; routes and services must call it rather than mutating status
    directly."""
    allowed = ALLOWED_TRANSITIONS.get((current, actor_role), frozenset())
    if target not in allowed:
        raise TransitionNotAllowed(
            f"{current.value} -> {target.value} not allowed for {actor_role.value}"
        )
