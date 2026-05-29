export const RUN_STATUS_LABEL = {
    queued: "Queued",
    running: "Running…",
    passed: "Passed",
    warning: "Warning",
    failed: "Failed",
    error: "Error",
    cancelled: "Cancelled",
};
export const STEP_STATUS_LABEL = {
    queued: "Queued",
    running: "Running…",
    passed: "Passed",
    warning: "Warning",
    failed: "Failed",
    error: "Error",
    skipped: "Skipped",
};
export const IMPACT_LABEL = {
    none: "No impact",
    warning: "Warning",
    blocked: "Blocked",
};
export const SEVERITY_LABEL = {
    none: "None",
    low: "Low",
    medium: "Medium",
    high: "High",
    critical: "Critical",
};
/** Whether a run has reached a terminal state (stop polling). */
export function isTerminal(status) {
    return !["queued", "running"].includes(status);
}
