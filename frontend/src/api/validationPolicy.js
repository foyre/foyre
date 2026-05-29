import { request } from "./client";
export const getValidationPolicy = () => request("/admin/validation/policy");
export const updateValidationPolicy = (patch) => request("/admin/validation/policy", {
    method: "PUT",
    body: JSON.stringify(patch),
});
