import type {
  Pipeline,
  PipelineSummary,
  PipelineValidateResult,
} from "../types/domain";
import { request } from "./client";

export const listPipelines = () =>
  request<PipelineSummary[]>("/validation/pipelines");

export const getPipeline = (id: number) =>
  request<Pipeline>(`/validation/pipelines/${id}`);

export const createPipeline = (input: {
  definition_yaml: string;
  enabled?: boolean;
  is_default?: boolean;
}) =>
  request<Pipeline>("/validation/pipelines", {
    method: "POST",
    body: JSON.stringify(input),
  });

export const updatePipeline = (
  id: number,
  patch: { definition_yaml?: string; enabled?: boolean },
) =>
  request<Pipeline>(`/validation/pipelines/${id}`, {
    method: "PUT",
    body: JSON.stringify(patch),
  });

export const deletePipeline = (id: number) =>
  request<void>(`/validation/pipelines/${id}`, { method: "DELETE" });

export const setDefaultPipeline = (id: number) =>
  request<Pipeline>(`/validation/pipelines/${id}/set-default`, {
    method: "POST",
  });

export const validatePipeline = (definition_yaml: string) =>
  request<PipelineValidateResult>("/validation/pipelines/validate", {
    method: "POST",
    body: JSON.stringify({ definition_yaml }),
  });
