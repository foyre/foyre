// Mirrors backend enums in app/domain/enums.py.

export type Role = "requester" | "reviewer" | "architect" | "admin";

export type RequestStatus =
  | "draft"
  | "submitted"
  | "ready_for_review"
  | "under_review"
  | "approved"
  | "rejected";

export type RiskLevel = "low" | "medium" | "high" | "unknown";

export interface User {
  id: number;
  username: string;
  email: string;
  role: Role;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
}

export interface UserRef {
  id: number;
  username: string;
  role: Role;
}

export interface IntakeRequest {
  id: number;
  created_by_id: number;
  created_by: UserRef | null;
  status: RequestStatus;
  payload: Record<string, unknown>;
  risk_level: RiskLevel | null;
  risk_reasons: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface Comment {
  id: number;
  request_id: number;
  author_id: number;
  author: UserRef | null;
  body: string;
  created_at: string;
}

export interface HistoryEvent {
  id: number;
  request_id: number;
  actor_id: number;
  actor: UserRef | null;
  event_type: string;
  detail: Record<string, unknown> | null;
  created_at: string;
}

export type FormFieldType = "text" | "textarea" | "select" | "boolean";

export interface FormField {
  name: string;
  label: string;
  type: FormFieldType;
  required?: boolean;
  options?: { value: string; label: string }[];
  visible_if?: Record<string, unknown>;
  /** "core" = built-in field locked by the backend; "custom" = admin-defined. */
  source?: "core" | "custom";
}

export interface FormSection {
  id: string;
  title: string;
  fields: FormField[];
}

export interface FormSchema {
  sections: FormSection[];
}

// --- Validation pipelines ------------------------------------------------

export type ValidationRunStatus =
  | "queued"
  | "running"
  | "passed"
  | "warning"
  | "failed"
  | "error"
  | "cancelled";

export type ValidationStepStatus =
  | "queued"
  | "running"
  | "passed"
  | "warning"
  | "failed"
  | "error"
  | "skipped";

export type ValidationSeverity = "none" | "low" | "medium" | "high" | "critical";

export type ApprovalImpact = "none" | "warning" | "blocked";

export interface PipelineSummary {
  id: number;
  name: string;
  display_name: string;
  description: string | null;
  enabled: boolean;
  is_default: boolean;
  version: number;
  default_failure_policy: string;
  created_at: string;
  updated_at: string;
}

export interface Pipeline extends PipelineSummary {
  definition_yaml: string;
  definition_json: Record<string, unknown>;
  created_by_id: number | null;
  updated_by_id: number | null;
}

export interface PipelineValidateResult {
  valid: boolean;
  normalized: Record<string, unknown> | null;
  error: string | null;
}

export interface ValidationFinding {
  severity: ValidationSeverity;
  title: string;
  resource?: string;
  message?: string;
  recommendation?: string;
}

export interface ValidationArtifact {
  id: number;
  validation_run_id: number;
  step_result_id: number | null;
  artifact_name: string;
  artifact_type: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface ValidationStepResult {
  id: number;
  step_name: string;
  step_type: string;
  display_name: string | null;
  sort_order: number;
  status: ValidationStepStatus;
  severity: ValidationSeverity;
  summary: string | null;
  findings_json: ValidationFinding[] | null;
  details_json: Record<string, unknown> | null;
  error_message: string | null;
  required: boolean;
  failure_policy: string;
  started_at: string | null;
  completed_at: string | null;
  artifacts: ValidationArtifact[];
}

export interface ValidationRunSummary {
  id: number;
  request_id: number;
  pipeline_id: number | null;
  pipeline_name: string;
  pipeline_version: number;
  status: ValidationRunStatus;
  approval_impact: ApprovalImpact;
  started_by_id: number | null;
  summary_json: Record<string, unknown> | null;
  started_at: string;
  completed_at: string | null;
}

export interface ValidationRun extends ValidationRunSummary {
  validation_environment_id: number | null;
  reason: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  step_results: ValidationStepResult[];
}

export interface ApprovalGate {
  blocked: boolean;
  impact: ApprovalImpact;
  reason: string | null;
  override_allowed: boolean;
  missing_validation: boolean;
  latest_run_id: number | null;
}

export interface ValidationPolicy {
  require_validation_before_approval: boolean;
  block_approval_on_failed_validation: boolean;
  allow_validation_override: boolean;
  updated_at: string | null;
  updated_by_id: number | null;
}

export const PRIVILEGED_ROLES: ReadonlyArray<Role> = [
  "reviewer",
  "architect",
  "admin",
];

export function isPrivileged(role: Role): boolean {
  return PRIVILEGED_ROLES.includes(role);
}
