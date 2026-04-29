import { jsx as _jsx } from "react/jsx-runtime";
const LABELS = {
    draft: "Draft",
    submitted: "Submitted",
    ready_for_review: "Ready for review",
    under_review: "Under review",
    approved: "Approved",
    rejected: "Rejected",
};
export function StatusBadge({ status }) {
    return (_jsx("span", { className: "badge", "data-status": status, children: LABELS[status] }));
}
