import { request } from "./client";
export const getValidationEnv = (requestId) => request(`/requests/${requestId}/validation-environment`);
export const createValidationEnv = (requestId) => request(`/requests/${requestId}/validation-environment`, { method: "POST" });
export const teardownValidationEnv = (requestId) => request(`/requests/${requestId}/validation-environment/teardown`, { method: "POST" });
export const downloadKubeconfig = (requestId) => request(`/requests/${requestId}/validation-environment/kubeconfig`);
