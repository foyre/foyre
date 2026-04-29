import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { createHostCluster, testUnsavedConnection, updateHostCluster, } from "../../api/hostClusters";
const DEFAULTS = {
    ttl_hours: 72,
    cpu_quota: "4",
    memory_quota: "8Gi",
    storage_quota: "10Gi",
    apply_default_network_policy: true,
    apply_default_resource_quota: true,
    allow_regenerate_kubeconfig: true,
};
export function HostClusterForm({ initial, onSaved, onCancel }) {
    const editing = Boolean(initial);
    const [name, setName] = useState(initial?.name ?? "");
    const [externalNodeHost, setExternalNodeHost] = useState(initial?.external_node_host ?? "");
    const [contextName, setContextName] = useState(initial?.context_name ?? "");
    const [isDefault, setIsDefault] = useState(initial?.is_default ?? false);
    const [isEnabled, setIsEnabled] = useState(initial?.is_enabled ?? true);
    const [kubeconfig, setKubeconfig] = useState("");
    const [defaults, setDefaults] = useState(initial
        ? {
            ttl_hours: initial.ttl_hours,
            cpu_quota: initial.cpu_quota,
            memory_quota: initial.memory_quota,
            storage_quota: initial.storage_quota,
            apply_default_network_policy: initial.apply_default_network_policy,
            apply_default_resource_quota: initial.apply_default_resource_quota,
            allow_regenerate_kubeconfig: initial.allow_regenerate_kubeconfig,
        }
        : DEFAULTS);
    const [testResult, setTestResult] = useState(null);
    const [testing, setTesting] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    // When editing, the kubeconfig field is empty by default — admin only pastes
    // a new one if they want to replace. We consider that "verified" because the
    // backend keeps the existing config and its last test result.
    const kubeconfigChanged = kubeconfig.trim().length > 0;
    const canSave = editing
        ? !kubeconfigChanged || testResult?.success === true
        : testResult?.success === true;
    const runTest = async () => {
        if (!kubeconfigChanged)
            return;
        setTesting(true);
        setError(null);
        setTestResult(null);
        try {
            const r = await testUnsavedConnection(kubeconfig, contextName || null);
            setTestResult(r);
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setTesting(false);
        }
    };
    const save = async (e) => {
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
            }
            else {
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
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs("form", { onSubmit: save, className: "card", style: { marginBottom: 16 }, children: [_jsx("h4", { style: { marginTop: 0 }, children: editing ? `Edit host cluster "${initial.name}"` : "Add host cluster" }), error && _jsx("div", { className: "error", children: error }), _jsxs("div", { style: {
                    display: "grid",
                    gridTemplateColumns: "repeat(2, 1fr)",
                    gap: 12,
                }, children: [_jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "Name" }), _jsx("input", { value: name, onChange: (e) => setName(e.target.value), placeholder: "e.g. rke2-prod", required: true })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "External node host" }), _jsx("input", { value: externalNodeHost, onChange: (e) => setExternalNodeHost(e.target.value), placeholder: "IP or hostname reachable by requesters" }), _jsx("span", { className: "muted", style: { fontSize: 12 }, children: "Blank = fall back to node InternalIP" })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "Context name (optional)" }), _jsx("input", { value: contextName, onChange: (e) => setContextName(e.target.value), placeholder: "uses kubeconfig's current-context if blank" })] }), _jsxs("label", { style: {
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            margin: 0,
                        }, children: [_jsx("input", { type: "checkbox", checked: isDefault, onChange: (e) => setIsDefault(e.target.checked), style: { width: "auto" } }), _jsx("span", { children: "Use as default host cluster" })] })] }), _jsxs("label", { className: "field", style: { marginTop: 16 }, children: [_jsxs("span", { className: "label", children: ["Kubeconfig ", editing && _jsx("span", { className: "muted", children: "(leave empty to keep current)" })] }), _jsx("textarea", { value: kubeconfig, onChange: (e) => {
                            setKubeconfig(e.target.value);
                            setTestResult(null);
                        }, rows: 10, placeholder: editing ? "Paste a new kubeconfig to replace…" : "Paste kubeconfig YAML here", style: {
                            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                            fontSize: 12,
                        }, required: !editing }), _jsxs("div", { className: "form-actions", style: { marginTop: 8 }, children: [_jsx("button", { type: "button", onClick: runTest, disabled: !kubeconfigChanged || testing, children: testing ? "Testing…" : "Test connection" }), testResult && _jsx(TestResultPill, { result: testResult })] })] }), testResult?.success && (_jsxs("dl", { className: "muted", style: {
                    display: "grid",
                    gridTemplateColumns: "max-content 1fr",
                    gap: "4px 16px",
                    fontSize: 13,
                    marginTop: 8,
                }, children: [_jsx("dt", { children: "Cluster version" }), _jsx("dd", { children: testResult.cluster_version }), _jsx("dt", { children: "Nodes" }), _jsx("dd", { children: testResult.node_count }), _jsx("dt", { children: "Storage class present" }), _jsx("dd", { children: testResult.has_storage_class ? "yes" : "no — install one before provisioning" }), _jsx("dt", { children: "Can create namespaces" }), _jsx("dd", { children: testResult.can_create_namespaces ? "yes" : "no — missing RBAC" }), _jsx("dt", { children: "Can create ClusterRoleBindings" }), _jsx("dd", { children: testResult.can_create_rbac ? "yes" : "no — missing RBAC" })] })), _jsxs("fieldset", { style: {
                    marginTop: 16,
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    padding: 12,
                }, children: [_jsx("legend", { style: { padding: "0 4px", fontWeight: 500 }, children: "Defaults for new validation clusters" }), _jsxs("div", { style: {
                            display: "grid",
                            gridTemplateColumns: "repeat(4, 1fr)",
                            gap: 12,
                        }, children: [_jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "TTL (hours)" }), _jsx("input", { type: "number", min: 1, value: defaults.ttl_hours, onChange: (e) => setDefaults({ ...defaults, ttl_hours: Number(e.target.value) }) })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "CPU quota" }), _jsx("input", { value: defaults.cpu_quota, onChange: (e) => setDefaults({ ...defaults, cpu_quota: e.target.value }) })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "Memory quota" }), _jsx("input", { value: defaults.memory_quota, onChange: (e) => setDefaults({ ...defaults, memory_quota: e.target.value }) })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "Storage quota" }), _jsx("input", { value: defaults.storage_quota, onChange: (e) => setDefaults({ ...defaults, storage_quota: e.target.value }) })] })] }), _jsxs("label", { style: { display: "flex", alignItems: "center", gap: 8, marginTop: 12 }, children: [_jsx("input", { type: "checkbox", checked: defaults.apply_default_network_policy, onChange: (e) => setDefaults({ ...defaults, apply_default_network_policy: e.target.checked }), style: { width: "auto" } }), _jsx("span", { children: "Apply default NetworkPolicy (deny egress outside namespace)" })] }), _jsxs("label", { style: { display: "flex", alignItems: "center", gap: 8, marginTop: 6 }, children: [_jsx("input", { type: "checkbox", checked: defaults.apply_default_resource_quota, onChange: (e) => setDefaults({ ...defaults, apply_default_resource_quota: e.target.checked }), style: { width: "auto" } }), _jsx("span", { children: "Apply default ResourceQuota" })] }), _jsxs("label", { style: { display: "flex", alignItems: "center", gap: 8, marginTop: 6 }, children: [_jsx("input", { type: "checkbox", checked: defaults.allow_regenerate_kubeconfig, onChange: (e) => setDefaults({ ...defaults, allow_regenerate_kubeconfig: e.target.checked }), style: { width: "auto" } }), _jsx("span", { children: "Allow requesters to regenerate their kubeconfig" })] })] }), _jsxs("label", { style: { display: "flex", alignItems: "center", gap: 8, marginTop: 12 }, children: [_jsx("input", { type: "checkbox", checked: isEnabled, onChange: (e) => setIsEnabled(e.target.checked), style: { width: "auto" } }), _jsx("span", { children: "Enabled (requesters can provision against this host)" })] }), _jsxs("div", { className: "form-actions", style: { marginTop: 16 }, children: [_jsx("button", { type: "submit", className: "primary", disabled: busy || !canSave, children: busy ? "Saving…" : editing ? "Save changes" : "Add host cluster" }), _jsx("button", { type: "button", onClick: onCancel, disabled: busy, children: "Cancel" }), !canSave && kubeconfigChanged && (_jsx("span", { className: "muted", style: { fontSize: 12 }, children: "Test the connection successfully before saving." }))] })] }));
}
function TestResultPill({ result }) {
    if (result.success) {
        return (_jsx("span", { className: "badge", "data-status": "approved", children: "Connected" }));
    }
    return (_jsx("span", { className: "badge", "data-status": "rejected", title: result.error ?? "connection failed", children: "Failed" }));
}
