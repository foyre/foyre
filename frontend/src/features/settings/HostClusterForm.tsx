import { useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import {
  type HostCluster,
  type HostClusterDefaults,
  type TestConnectionResult,
  createHostCluster,
  testUnsavedConnection,
  updateHostCluster,
} from "../../api/hostClusters";

interface Props {
  /** If provided, we're editing an existing row. Otherwise we're creating. */
  initial?: HostCluster;
  onSaved: () => void;
  onCancel: () => void;
}

const DEFAULTS: HostClusterDefaults = {
  ttl_hours: 72,
  cpu_quota: "4",
  memory_quota: "8Gi",
  storage_quota: "10Gi",
  apply_default_network_policy: true,
  apply_default_resource_quota: true,
  allow_regenerate_kubeconfig: true,
};

export function HostClusterForm({ initial, onSaved, onCancel }: Props) {
  const editing = Boolean(initial);
  const [name, setName] = useState(initial?.name ?? "");
  const [externalNodeHost, setExternalNodeHost] = useState(
    initial?.external_node_host ?? "",
  );
  const [contextName, setContextName] = useState(initial?.context_name ?? "");
  const [isDefault, setIsDefault] = useState(initial?.is_default ?? false);
  const [isEnabled, setIsEnabled] = useState(initial?.is_enabled ?? true);
  const [kubeconfig, setKubeconfig] = useState("");

  const [defaults, setDefaults] = useState<HostClusterDefaults>(
    initial
      ? {
          ttl_hours: initial.ttl_hours,
          cpu_quota: initial.cpu_quota,
          memory_quota: initial.memory_quota,
          storage_quota: initial.storage_quota,
          apply_default_network_policy: initial.apply_default_network_policy,
          apply_default_resource_quota: initial.apply_default_resource_quota,
          allow_regenerate_kubeconfig: initial.allow_regenerate_kubeconfig,
        }
      : DEFAULTS,
  );

  const [testResult, setTestResult] = useState<TestConnectionResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // When editing, the kubeconfig field is empty by default — admin only pastes
  // a new one if they want to replace. We consider that "verified" because the
  // backend keeps the existing config and its last test result.
  const kubeconfigChanged = kubeconfig.trim().length > 0;
  const canSave = editing
    ? !kubeconfigChanged || testResult?.success === true
    : testResult?.success === true;

  const runTest = async () => {
    if (!kubeconfigChanged) return;
    setTesting(true);
    setError(null);
    setTestResult(null);
    try {
      const r = await testUnsavedConnection(kubeconfig, contextName || null);
      setTestResult(r);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setTesting(false);
    }
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (editing && initial) {
        await updateHostCluster(initial.id, {
          name,
          external_node_host: externalNodeHost || null,
          context_name: contextName || null,
          is_default: isDefault,
          is_enabled: isEnabled,
          defaults,
          ...(kubeconfigChanged ? { kubeconfig } : {}),
        });
      } else {
        await createHostCluster({
          name,
          kubeconfig,
          external_node_host: externalNodeHost || null,
          context_name: contextName || null,
          is_default: isDefault,
          is_enabled: isEnabled,
          defaults,
        });
      }
      onSaved();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={save} className="card" style={{ marginBottom: 16 }}>
      <h4 style={{ marginTop: 0 }}>
        {editing ? `Edit host cluster "${initial!.name}"` : "Add host cluster"}
      </h4>

      {error && <div className="error">{error}</div>}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 12,
        }}
      >
        <label className="field" style={{ margin: 0 }}>
          <span className="label">Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. rke2-prod"
            required
          />
        </label>
        <label className="field" style={{ margin: 0 }}>
          <span className="label">External node host</span>
          <input
            value={externalNodeHost}
            onChange={(e) => setExternalNodeHost(e.target.value)}
            placeholder="IP or hostname reachable by requesters"
          />
          <span className="muted" style={{ fontSize: 12 }}>
            Blank = fall back to node InternalIP
          </span>
        </label>
        <label className="field" style={{ margin: 0 }}>
          <span className="label">Context name (optional)</span>
          <input
            value={contextName}
            onChange={(e) => setContextName(e.target.value)}
            placeholder="uses kubeconfig's current-context if blank"
          />
        </label>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            margin: 0,
          }}
        >
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
            style={{ width: "auto" }}
          />
          <span>Use as default host cluster</span>
        </label>
      </div>

      <label className="field" style={{ marginTop: 16 }}>
        <span className="label">
          Kubeconfig {editing && <span className="muted">(leave empty to keep current)</span>}
        </span>
        <textarea
          value={kubeconfig}
          onChange={(e) => {
            setKubeconfig(e.target.value);
            setTestResult(null);
          }}
          rows={10}
          placeholder={editing ? "Paste a new kubeconfig to replace…" : "Paste kubeconfig YAML here"}
          style={{
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: 12,
          }}
          required={!editing}
        />
        <div className="form-actions" style={{ marginTop: 8 }}>
          <button
            type="button"
            onClick={runTest}
            disabled={!kubeconfigChanged || testing}
          >
            {testing ? "Testing…" : "Test connection"}
          </button>
          {testResult && <TestResultPill result={testResult} />}
        </div>
      </label>

      {testResult?.success && (
        <dl
          className="muted"
          style={{
            display: "grid",
            gridTemplateColumns: "max-content 1fr",
            gap: "4px 16px",
            fontSize: 13,
            marginTop: 8,
          }}
        >
          <dt>Cluster version</dt>
          <dd>{testResult.cluster_version}</dd>
          <dt>Nodes</dt>
          <dd>{testResult.node_count}</dd>
          <dt>Storage class present</dt>
          <dd>{testResult.has_storage_class ? "yes" : "no — install one before provisioning"}</dd>
          <dt>Can create namespaces</dt>
          <dd>{testResult.can_create_namespaces ? "yes" : "no — missing RBAC"}</dd>
          <dt>Can create ClusterRoleBindings</dt>
          <dd>{testResult.can_create_rbac ? "yes" : "no — missing RBAC"}</dd>
        </dl>
      )}

      <fieldset
        style={{
          marginTop: 16,
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
          padding: 12,
        }}
      >
        <legend style={{ padding: "0 4px", fontWeight: 500 }}>
          Defaults for new validation clusters
        </legend>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 12,
          }}
        >
          <label className="field" style={{ margin: 0 }}>
            <span className="label">TTL (hours)</span>
            <input
              type="number"
              min={1}
              value={defaults.ttl_hours}
              onChange={(e) => setDefaults({ ...defaults, ttl_hours: Number(e.target.value) })}
            />
          </label>
          <label className="field" style={{ margin: 0 }}>
            <span className="label">CPU quota</span>
            <input
              value={defaults.cpu_quota}
              onChange={(e) => setDefaults({ ...defaults, cpu_quota: e.target.value })}
            />
          </label>
          <label className="field" style={{ margin: 0 }}>
            <span className="label">Memory quota</span>
            <input
              value={defaults.memory_quota}
              onChange={(e) => setDefaults({ ...defaults, memory_quota: e.target.value })}
            />
          </label>
          <label className="field" style={{ margin: 0 }}>
            <span className="label">Storage quota</span>
            <input
              value={defaults.storage_quota}
              onChange={(e) => setDefaults({ ...defaults, storage_quota: e.target.value })}
            />
          </label>
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
          <input
            type="checkbox"
            checked={defaults.apply_default_network_policy}
            onChange={(e) =>
              setDefaults({ ...defaults, apply_default_network_policy: e.target.checked })
            }
            style={{ width: "auto" }}
          />
          <span>Apply default NetworkPolicy (deny egress outside namespace)</span>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
          <input
            type="checkbox"
            checked={defaults.apply_default_resource_quota}
            onChange={(e) =>
              setDefaults({ ...defaults, apply_default_resource_quota: e.target.checked })
            }
            style={{ width: "auto" }}
          />
          <span>Apply default ResourceQuota</span>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
          <input
            type="checkbox"
            checked={defaults.allow_regenerate_kubeconfig}
            onChange={(e) =>
              setDefaults({ ...defaults, allow_regenerate_kubeconfig: e.target.checked })
            }
            style={{ width: "auto" }}
          />
          <span>Allow requesters to regenerate their kubeconfig</span>
        </label>
      </fieldset>

      <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
        <input
          type="checkbox"
          checked={isEnabled}
          onChange={(e) => setIsEnabled(e.target.checked)}
          style={{ width: "auto" }}
        />
        <span>Enabled (requesters can provision against this host)</span>
      </label>

      <div className="form-actions" style={{ marginTop: 16 }}>
        <button type="submit" className="primary" disabled={busy || !canSave}>
          {busy ? "Saving…" : editing ? "Save changes" : "Add host cluster"}
        </button>
        <button type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        {!canSave && kubeconfigChanged && (
          <span className="muted" style={{ fontSize: 12 }}>
            Test the connection successfully before saving.
          </span>
        )}
      </div>
    </form>
  );
}

function TestResultPill({ result }: { result: TestConnectionResult }) {
  if (result.success) {
    return (
      <span className="badge" data-status="approved">
        Connected
      </span>
    );
  }
  return (
    <span
      className="badge"
      data-status="rejected"
      title={result.error ?? "connection failed"}
    >
      Failed
    </span>
  );
}
