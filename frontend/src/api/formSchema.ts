import type { FormSchema, FormSection } from "../types/domain";
import { request } from "./client";

export interface FormSchemaConfigOut {
  sections: FormSection[];
  is_customized: boolean;
  updated_at: string | null;
  updated_by_id: number | null;
  updated_by_username: string | null;
}

export interface FormSchemaAdminBundle {
  current: FormSchemaConfigOut;
  default: FormSchema;
  core_field_names: string[];
}

export const getAdminFormSchema = () =>
  request<FormSchemaAdminBundle>("/admin/form-schema");

export const updateAdminFormSchema = (sections: FormSection[]) =>
  request<FormSchemaAdminBundle>("/admin/form-schema", {
    method: "PUT",
    body: JSON.stringify({ sections }),
  });

export const resetAdminFormSchema = () =>
  request<FormSchemaAdminBundle>("/admin/form-schema/reset", {
    method: "POST",
  });
