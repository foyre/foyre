/**
 * Given a request's current status and the logged-in user's role, return the
 * set of status-change actions the UI should offer.
 *
 * The backend workflow table is the source of truth — this is a UX mirror to
 * avoid showing buttons that will 400. A wrong entry here only hides a legal
 * action or shows an illegal one; either way the API still enforces the rule.
 */
import type { RequestStatus, Role } from "../types/domain";

export interface Action {
  to: RequestStatus;
  label: string;
  kind: "primary" | "default";
}

const PRIVILEGED: ReadonlyArray<Role> = ["reviewer", "architect", "admin"];

export function availableTransitions(
  status: RequestStatus,
  role: Role,
): Action[] {
  if (
    (status === "submitted" || status === "ready_for_review") &&
    PRIVILEGED.includes(role)
  ) {
    return [
      { to: "under_review", label: "Move to under review", kind: "default" },
      { to: "approved", label: "Approve", kind: "primary" },
      { to: "rejected", label: "Reject", kind: "default" },
    ];
  }
  if (status === "under_review" && PRIVILEGED.includes(role)) {
    return [
      { to: "approved", label: "Approve", kind: "primary" },
      { to: "rejected", label: "Reject", kind: "default" },
    ];
  }
  return [];
}
