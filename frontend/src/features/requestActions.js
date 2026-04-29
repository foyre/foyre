const PRIVILEGED = ["reviewer", "architect", "admin"];
export function availableTransitions(status, role) {
    if ((status === "submitted" || status === "ready_for_review") &&
        PRIVILEGED.includes(role)) {
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
