import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { deleteHostCluster, listHostClusters, testSavedConnection, } from "../../api/hostClusters";
import { HostClusterForm } from "./HostClusterForm";
import { HostClusterSetupGuide } from "./HostClusterSetupGuide";
export function HostClusterList() {
    const [items, setItems] = useState(null);
    const [error, setError] = useState(null);
    const [flash, setFlash] = useState(null);
    const [mode, setMode] = useState({ kind: "list" });
    const reload = async () => {
        try {
            setItems(await listHostClusters());
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
    };
    useEffect(() => {
        reload();
    }, []);
    const guarded = async (fn, successMsg) => {
        setError(null);
        setFlash(null);
        try {
            await fn();
            if (successMsg)
                setFlash(successMsg);
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
    };
    return (_jsxs("div", { children: [error && _jsx("div", { className: "error", children: error }), flash && (_jsx("div", { className: "muted", style: { marginBottom: 12 }, children: flash })), _jsx(HostClusterSetupGuide, {}), mode.kind === "list" && (_jsxs(_Fragment, { children: [_jsx("div", { className: "form-actions", style: { marginBottom: 12 }, children: _jsx("button", { className: "primary", onClick: () => setMode({ kind: "create" }), children: "Add host cluster" }) }), items === null ? (_jsx("p", { className: "muted", children: "Loading\u2026" })) : items.length === 0 ? (_jsx("div", { className: "empty", children: "No host clusters configured. Add one to start provisioning validation environments." })) : (_jsxs("table", { className: "data", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: { width: 64 }, children: "ID" }), _jsx("th", { children: "Name" }), _jsx("th", { children: "Provider" }), _jsx("th", { children: "Connection" }), _jsx("th", { children: "Default" }), _jsx("th", { children: "Enabled" }), _jsx("th", { children: "Last tested" }), _jsx("th", { style: { width: 220 } })] }) }), _jsx("tbody", { children: items.map((h) => (_jsxs("tr", { style: { opacity: h.is_enabled ? 1 : 0.6 }, children: [_jsxs("td", { children: ["#", h.id] }), _jsxs("td", { children: [_jsx("strong", { children: h.name }), h.last_test_cluster_version && (_jsxs("div", { className: "muted", style: { fontSize: 12 }, children: [h.last_test_cluster_version, ",", " ", h.last_test_node_count ?? "?", " node", h.last_test_node_count === 1 ? "" : "s"] }))] }), _jsx("td", { children: h.provider }), _jsx("td", { children: _jsx(ConnStatus, { row: h }) }), _jsx("td", { children: h.is_default ? "yes" : "" }), _jsx("td", { children: h.is_enabled ? "yes" : "no" }), _jsx("td", { className: "muted", style: { fontSize: 12 }, children: h.last_tested_at
                                                ? new Date(h.last_tested_at).toLocaleString()
                                                : "—" }), _jsx("td", { children: _jsxs("div", { style: { display: "flex", gap: 6 }, children: [_jsx("button", { onClick: () => guarded(async () => {
                                                            await testSavedConnection(h.id);
                                                            await reload();
                                                        }, `Tested ${h.name}.`), children: "Test" }), _jsx("button", { onClick: () => setMode({ kind: "edit", row: h }), children: "Edit" }), _jsx("button", { onClick: () => guarded(async () => {
                                                            if (!window.confirm(`Remove host cluster "${h.name}"? ` +
                                                                `Any validation environments already provisioned on it will continue running.`))
                                                                return;
                                                            await deleteHostCluster(h.id);
                                                            await reload();
                                                        }, `Removed ${h.name}.`), children: "Remove" })] }) })] }, h.id))) })] }))] })), mode.kind === "create" && (_jsx(HostClusterForm, { onSaved: () => {
                    setMode({ kind: "list" });
                    guarded(reload, "Host cluster added.");
                }, onCancel: () => setMode({ kind: "list" }) })), mode.kind === "edit" && (_jsx(HostClusterForm, { initial: mode.row, onSaved: () => {
                    setMode({ kind: "list" });
                    guarded(reload, "Host cluster updated.");
                }, onCancel: () => setMode({ kind: "list" }) }))] }));
}
function ConnStatus({ row }) {
    switch (row.last_test_status) {
        case "connected":
            return (_jsx("span", { className: "badge", "data-status": "approved", title: row.last_test_error ?? "", children: "Connected" }));
        case "failed":
            return (_jsx("span", { className: "badge", "data-status": "rejected", title: row.last_test_error ?? "connection failed", children: "Failed" }));
        default:
            return (_jsx("span", { className: "badge", "data-status": "draft", children: "Untested" }));
    }
}
