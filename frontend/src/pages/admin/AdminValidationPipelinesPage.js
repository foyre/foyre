import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { deletePipeline, getPipeline, listPipelines, setDefaultPipeline, updatePipeline, } from "../../api/validationPipelines";
import { PipelineEditor } from "../../features/validationPipelines/PipelineEditor";
import { PolicyControls } from "../../features/validationPipelines/PolicyControls";
export function AdminValidationPipelinesPage() {
    const [pipelines, setPipelines] = useState(null);
    const [editor, setEditor] = useState({ mode: "closed" });
    const [error, setError] = useState(null);
    const reload = async () => {
        try {
            setPipelines(await listPipelines());
        }
        catch (e) {
            setError(apiErrorMessage(e));
        }
    };
    useEffect(() => {
        reload();
    }, []);
    const guarded = async (fn) => {
        setError(null);
        try {
            await fn();
            await reload();
        }
        catch (e) {
            setError(apiErrorMessage(e));
        }
    };
    const openEdit = async (id) => {
        setError(null);
        try {
            const full = await getPipeline(id);
            setEditor({ mode: "edit", pipeline: full });
        }
        catch (e) {
            setError(apiErrorMessage(e));
        }
    };
    return (_jsxs("div", { children: [_jsx("p", { className: "muted", style: { marginTop: 0, marginBottom: 16 }, children: "Define reusable validation pipelines that reviewers run against a request's validation environment. Pipelines collect evidence (workload inventory, security posture, image scans, custom checks) before approval." }), _jsx(PolicyControls, {}), error && _jsx("div", { className: "error", children: error }), _jsxs("div", { className: "header-row", style: { marginBottom: 12 }, children: [_jsx("h3", { style: { margin: 0 }, children: "Pipelines" }), editor.mode === "closed" && (_jsx("button", { className: "primary", onClick: () => setEditor({ mode: "create" }), children: "New pipeline" }))] }), editor.mode !== "closed" && (_jsx(PipelineEditor, { pipeline: editor.mode === "edit" ? editor.pipeline : undefined, onSaved: () => {
                    setEditor({ mode: "closed" });
                    reload();
                }, onCancel: () => setEditor({ mode: "closed" }) })), pipelines === null ? (_jsx("p", { className: "muted", children: "Loading\u2026" })) : pipelines.length === 0 ? (_jsx("div", { className: "empty", children: "No pipelines yet. Create one to get started." })) : (_jsxs("table", { className: "data", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "Name" }), _jsx("th", { children: "Version" }), _jsx("th", { children: "Status" }), _jsx("th", { children: "Default" }), _jsx("th", { style: { width: 260 } })] }) }), _jsx("tbody", { children: pipelines.map((p) => (_jsxs("tr", { style: { opacity: p.enabled ? 1 : 0.55 }, children: [_jsxs("td", { children: [_jsx("strong", { children: p.display_name }), _jsx("div", { className: "muted", style: { fontSize: 12 }, children: _jsx("code", { children: p.name }) })] }), _jsxs("td", { children: ["v", p.version] }), _jsx("td", { children: p.enabled ? (_jsx("span", { className: "badge", "data-status": "approved", children: "Enabled" })) : (_jsx("span", { className: "badge", "data-status": "draft", children: "Disabled" })) }), _jsx("td", { children: p.is_default ? (_jsx("span", { className: "badge", "data-status": "submitted", children: "Default" })) : (_jsx("span", { className: "muted", children: "\u2014" })) }), _jsx("td", { children: _jsxs("div", { style: { display: "flex", gap: 6, flexWrap: "wrap" }, children: [_jsx("button", { onClick: () => openEdit(p.id), children: "Edit" }), !p.is_default && p.enabled && (_jsx("button", { onClick: () => guarded(async () => {
                                                    await setDefaultPipeline(p.id);
                                                }), children: "Set default" })), _jsx("button", { onClick: () => guarded(async () => {
                                                    await updatePipeline(p.id, { enabled: !p.enabled });
                                                }), children: p.enabled ? "Disable" : "Enable" }), _jsx("button", { className: "danger-btn", onClick: () => guarded(async () => {
                                                    if (!window.confirm(`Delete pipeline "${p.display_name}"? Past runs keep their snapshot and are unaffected.`))
                                                        return;
                                                    await deletePipeline(p.id);
                                                }), children: "Delete" })] }) })] }, p.id))) })] }))] }));
}
