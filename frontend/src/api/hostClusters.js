import { request } from "./client";
export const listHostClusters = () => request("/admin/host-clusters");
export const createHostCluster = (input) => request("/admin/host-clusters", {
    method: "POST",
    body: JSON.stringify(input),
});
export const updateHostCluster = (id, patch) => request(`/admin/host-clusters/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
});
export const deleteHostCluster = (id) => request(`/admin/host-clusters/${id}`, { method: "DELETE" });
export const testUnsavedConnection = (kubeconfig, context_name) => request("/admin/host-clusters/test-connection", {
    method: "POST",
    body: JSON.stringify({ kubeconfig, context_name }),
});
export const testSavedConnection = (id) => request(`/admin/host-clusters/${id}/test-connection`, {
    method: "POST",
});
