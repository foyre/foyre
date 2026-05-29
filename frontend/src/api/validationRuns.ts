import type {
  ApprovalGate,
  ValidationArtifact,
  ValidationRun,
  ValidationRunSummary,
} from "../types/domain";
import { getToken, request } from "./client";

export const startValidationRun = (
  requestId: number,
  body: { pipeline_id?: number | null; reason?: string | null } = {},
) =>
  request<ValidationRun>(`/requests/${requestId}/validation-runs`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const listValidationRuns = (requestId: number) =>
  request<ValidationRunSummary[]>(`/requests/${requestId}/validation-runs`);

export const getValidationRun = (runId: number) =>
  request<ValidationRun>(`/validation-runs/${runId}`);

export const listRunArtifacts = (runId: number) =>
  request<ValidationArtifact[]>(`/validation-runs/${runId}/artifacts`);

export const getApprovalGate = (requestId: number) =>
  request<ApprovalGate>(`/requests/${requestId}/validation-approval`);

/**
 * Artifact download returns raw bytes (not JSON), so we build the URL +
 * auth header ourselves and trigger a browser download via a blob.
 */
export async function downloadArtifact(
  artifact: ValidationArtifact,
): Promise<void> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`/api/validation-artifacts/${artifact.id}/download`, {
    headers,
  });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = artifact.artifact_name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
