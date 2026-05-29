import type { ValidationPolicy } from "../types/domain";
import { request } from "./client";

export const getValidationPolicy = () =>
  request<ValidationPolicy>("/admin/validation/policy");

export const updateValidationPolicy = (patch: {
  require_validation_before_approval?: boolean;
  block_approval_on_failed_validation?: boolean;
  allow_validation_override?: boolean;
}) =>
  request<ValidationPolicy>("/admin/validation/policy", {
    method: "PUT",
    body: JSON.stringify(patch),
  });
