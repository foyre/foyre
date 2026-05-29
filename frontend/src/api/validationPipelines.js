import { request } from "./client";
export const listPipelines = () => request("/validation/pipelines");
export const getPipeline = (id) => request(`/validation/pipelines/${id}`);
export const createPipeline = (input) => request("/validation/pipelines", {
    method: "POST",
    body: JSON.stringify(input),
});
export const updatePipeline = (id, patch) => request(`/validation/pipelines/${id}`, {
    method: "PUT",
    body: JSON.stringify(patch),
});
export const deletePipeline = (id) => request(`/validation/pipelines/${id}`, { method: "DELETE" });
export const setDefaultPipeline = (id) => request(`/validation/pipelines/${id}/set-default`, {
    method: "POST",
});
export const validatePipeline = (definition_yaml) => request("/validation/pipelines/validate", {
    method: "POST",
    body: JSON.stringify({ definition_yaml }),
});
