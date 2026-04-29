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

export interface FormField {
  name: string;
  label: string;
  type: "text" | "textarea" | "select" | "boolean";
  required?: boolean;
  options?: { value: string; label: string }[];
  visible_if?: Record<string, unknown>;
}

export interface FormSection {
  id: string;
  title: string;
  fields: FormField[];
}

export interface FormSchema {
  sections: FormSection[];
}

export const PRIVILEGED_ROLES: ReadonlyArray<Role> = [
  "reviewer",
  "architect",
  "admin",
];

export function isPrivileged(role: Role): boolean {
  return PRIVILEGED_ROLES.includes(role);
}
