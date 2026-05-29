import type {
  ApprovalImpact,
  ValidationRunStatus,
  ValidationSeverity,
  ValidationStepStatus,
} from "../../types/domain";

export const RUN_STATUS_LABEL: Record<ValidationRunStatus, string> = {
  queued: "Queued",
  running: "Running…",
  passed: "Passed",
  warning: "Warning",
  failed: "Failed",
  error: "Error",
  cancelled: "Cancelled",
};

export const STEP_STATUS_LABEL: Record<ValidationStepStatus, string> = {
  queued: "Queued",
  running: "Running…",
  passed: "Passed",
  warning: "Warning",
  failed: "Failed",
  error: "Error",
  skipped: "Skipped",
};

export const IMPACT_LABEL: Record<ApprovalImpact, string> = {
  none: "No impact",
  warning: "Warning",
  blocked: "Blocked",
};

export const SEVERITY_LABEL: Record<ValidationSeverity, string> = {
  none: "None",
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

/** Whether a run has reached a terminal state (stop polling). */
export function isTerminal(status: ValidationRunStatus): boolean {
  return !["queued", "running"].includes(status);
}
