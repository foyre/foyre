import type { FormSchema } from "../types/domain";
import { request } from "./client";

export const getFormSchema = () => request<FormSchema>("/meta/form-schema");
