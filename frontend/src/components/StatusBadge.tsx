import type { RequestStatus } from "../types/domain";

const LABELS: Record<RequestStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  ready_for_review: "Ready for review",
  under_review: "Under review",
  approved: "Approved",
  rejected: "Rejected",
};

export function StatusBadge({ status }: { status: RequestStatus }) {
  return (
    <span className="badge" data-status={status}>
      {LABELS[status]}
    </span>
  );
}
