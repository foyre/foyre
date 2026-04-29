import { request } from "./client";

export type ValidationEnvStatus =
  | "provisioning"
  | "ready"
  | "failed"
  | "torn_down";

export interface ValidationEnvironment {
  id: number;
  request_id: number;
  host_cluster_config_id: number;
  status: ValidationEnvStatus;
  namespace: string;
  vcluster_name: string;
  provider: string;
  external_endpoint: string | null;
  expires_at: string | null;
  extensions_used: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  torn_down_at: string | null;
}

export interface Kubeconfig {
  kubeconfig: string;
}

export const getValidationEnv = (requestId: number) =>
  request<ValidationEnvironment | null>(
    `/requests/${requestId}/validation-environment`,
  );

export const createValidationEnv = (requestId: number) =>
  request<ValidationEnvironment>(
    `/requests/${requestId}/validation-environment`,
    { method: "POST" },
  );

export const teardownValidationEnv = (requestId: number) =>
  request<ValidationEnvironment>(
    `/requests/${requestId}/validation-environment/teardown`,
    { method: "POST" },
  );

export const downloadKubeconfig = (requestId: number) =>
  request<Kubeconfig>(
    `/requests/${requestId}/validation-environment/kubeconfig`,
  );
