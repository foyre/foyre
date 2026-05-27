import { request } from "./client";
export const getAdminFormSchema = () => request("/admin/form-schema");
export const updateAdminFormSchema = (sections) => request("/admin/form-schema", {
    method: "PUT",
    body: JSON.stringify({ sections }),
});
export const resetAdminFormSchema = () => request("/admin/form-schema/reset", {
    method: "POST",
});
