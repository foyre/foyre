import { getToken, request } from "./client";
export const startValidationRun = (requestId, body = {}) => request(`/requests/${requestId}/validation-runs`, {
    method: "POST",
    body: JSON.stringify(body),
});
export const listValidationRuns = (requestId) => request(`/requests/${requestId}/validation-runs`);
export const getValidationRun = (runId) => request(`/validation-runs/${runId}`);
export const listRunArtifacts = (runId) => request(`/validation-runs/${runId}/artifacts`);
export const getApprovalGate = (requestId) => request(`/requests/${requestId}/validation-approval`);
/**
 * Artifact download returns raw bytes (not JSON), so we build the URL +
 * auth header ourselves and trigger a browser download via a blob.
 */
export async function downloadArtifact(artifact) {
    const headers = new Headers();
    const token = getToken();
    if (token)
        headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(`/api/validation-artifacts/${artifact.id}/download`, {
        headers,
    });
    if (!res.ok)
        throw new Error(`Download failed (${res.status})`);
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
