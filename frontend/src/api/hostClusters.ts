import { request } from "./client";

export interface HostClusterDefaults {
  ttl_hours: number;
  cpu_quota: string;
  memory_quota: string;
  storage_quota: string;
  apply_default_network_policy: boolean;
  apply_default_resource_quota: boolean;
  allow_regenerate_kubeconfig: boolean;
}

export interface HostCluster {
  id: number;
  name: string;
  provider: string;
  context_name: string | null;
  external_node_host: string | null;
  is_default: boolean;
  is_enabled: boolean;

  ttl_hours: number;
  cpu_quota: string;
  memory_quota: string;
  storage_quota: string;
  apply_default_network_policy: boolean;
  apply_default_resource_quota: boolean;
  allow_regenerate_kubeconfig: boolean;

  last_tested_at: string | null;
  last_test_status: "untested" | "connected" | "failed";
  last_test_error: string | null;
  last_test_cluster_version: string | null;
  last_test_node_count: number | null;
  last_test_has_storage_class: boolean | null;

  created_at: string;
  updated_at: string;
}

export interface TestConnectionResult {
  success: boolean;
  cluster_version: string | null;
  node_count: number | null;
  has_storage_class: boolean | null;
  can_create_namespaces: boolean | null;
  can_create_rbac: boolean | null;
  error: string | null;
}

export interface HostClusterCreateInput {
  name: string;
  provider?: string;
  kubeconfig: string;
  context_name?: string | null;
  external_node_host?: string | null;
  is_default?: boolean;
  is_enabled?: boolean;
  defaults?: HostClusterDefaults;
}

export interface HostClusterUpdateInput {
  name?: string;
  provider?: string;
  kubeconfig?: string;
  context_name?: string | null;
  external_node_host?: string | null;
  is_default?: boolean;
  is_enabled?: boolean;
  defaults?: HostClusterDefaults;
}

export const listHostClusters = () =>
  request<HostCluster[]>("/admin/host-clusters");

export const createHostCluster = (input: HostClusterCreateInput) =>
  request<HostCluster>("/admin/host-clusters", {
    method: "POST",
    body: JSON.stringify(input),
  });

export const updateHostCluster = (id: number, patch: HostClusterUpdateInput) =>
  request<HostCluster>(`/admin/host-clusters/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });

export const deleteHostCluster = (id: number) =>
  request<void>(`/admin/host-clusters/${id}`, { method: "DELETE" });

export const testUnsavedConnection = (
  kubeconfig: string,
  context_name?: string | null,
) =>
  request<TestConnectionResult>("/admin/host-clusters/test-connection", {
    method: "POST",
    body: JSON.stringify({ kubeconfig, context_name }),
  });

export const testSavedConnection = (id: number) =>
  request<HostCluster>(`/admin/host-clusters/${id}/test-connection`, {
    method: "POST",
  });
