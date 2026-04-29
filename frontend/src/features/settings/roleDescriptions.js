export const ROLE_DESCRIPTIONS = {
    requester: {
        role: "requester",
        label: "Requester",
        short: "Submits intake requests. Sees only their own requests. No review or admin access.",
        bullets: [
            "Create, edit, and submit their own intake requests",
            "View their own requests with status, comments, and history",
            "Read comments posted by reviewers",
            "Cannot view others' requests, post comments, or change status",
        ],
    },
    reviewer: {
        role: "reviewer",
        label: "Reviewer",
        short: "Reviews and decides on submitted requests. Can comment on any request.",
        bullets: [
            "View all intake requests",
            "Move submitted requests to under-review",
            "Approve or reject submitted or under-review requests",
            "Post comments on any request",
            "Cannot manage users or change roles",
        ],
    },
    architect: {
        role: "architect",
        label: "Architect",
        short: "Same permissions as Reviewer today. Reserved for future architecture sign-off.",
        bullets: [
            "Identical to Reviewer in the current workflow",
            "Reserved for future use (e.g. architecture sign-off distinct from security review)",
        ],
    },
    admin: {
        role: "admin",
        label: "Admin",
        short: "Full access. Manages users and roles, plus everything a Reviewer can do.",
        bullets: [
            "All Reviewer capabilities",
            "Create, deactivate, and reactivate local users",
            "Change other users' roles",
            "Cannot demote or deactivate themselves (self-lockout guard)",
        ],
    },
};
export const ROLE_ORDER = ["requester", "reviewer", "architect", "admin"];
/** Multi-line summary for a combined tooltip on a label/header. */
export const ALL_ROLES_TOOLTIP = ROLE_ORDER.map((r) => `${ROLE_DESCRIPTIONS[r].label}: ${ROLE_DESCRIPTIONS[r].short}`).join("\n\n");
