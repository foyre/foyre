import { request } from "./client";
export const getFormSchema = () => request("/meta/form-schema");
