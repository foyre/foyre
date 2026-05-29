import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { listPipelines } from "../../api/validationPipelines";
import { getValidationRun, listValidationRuns, startValidationRun, } from "../../api/validationRuns";
import { useAuth } from "../../auth/useAuth";
import { isPrivileged, } from "../../types/domain";
import { StepResultCard } from "./StepResultCard";
import { IMPACT_LABEL, RUN_STATUS_LABEL, isTerminal } from "./validationFormat";
const POLL_MS = 3000;
export function ValidationRunsPanel({ request: req, reloadKey, onRunChanged }) {
    const { user } = useAuth();
    const canRun = Boolean(user && isPrivileged(user.role));
    const [latest, setLatest] = useState(undefined);
    const [pipelines, setPipelines] = useState([]);
    const [pipelineId, setPipelineId] = useState("");
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    const pollRef = useRef(null);
    const stopPolling = () => {
        if (pollRef.current !== null) {
            window.clearInterval(pollRef.current);
            pollRef.current = null;
        }
    };
    useEffect(() => stopPolling, []);
    const loadLatest = async () => {
        try {
            const runs = await listValidationRuns(req.id);
            if (runs.length === 0) {
                setLatest(null);
                return null;
            }
            const full = await getValidationRun(runs[0].id);
            setLatest(full);
            if (isTerminal(full.status)) {
                stopPolling();
                onRunChanged?.();
            }
            return full;
        }
        catch (err) {
            setError(apiErrorMessage(err));
            stopPolling();
            return null;
        }
    };
    useEffect(() => {
        loadLatest().then((run) => {
            if (run && !isTerminal(run.status))
                startPolling();
        });
        if (canRun) {
            listPipelines()
                .then((ps) => setPipelines(ps.filter((p) => p.enabled)))
                .catch(() => setPipelines([]));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [req.id, reloadKey]);
    const startPolling = () => {
        stopPolling();
        pollRef.current = window.setInterval(loadLatest, POLL_MS);
    };
    const onRun = async () => {
        setBusy(true);
        setError(null);
        try {
            const run = await startValidationRun(req.id, {
                pipeline_id: pipelineId === "" ? null : pipelineId,
            });
            setLatest(run);
            onRunChanged?.();
            startPolling();
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    // Only meaningful once the request has progressed past draft.
    if (req.status === "draft")
        return null;
    const defaultPipeline = pipelines.find((p) => p.is_default);
    return (_jsxs("div", { className: "section-block", children: [_jsx("h3", { children: "Validation pipeline" }), error && _jsx("div", { className: "error", children: error }), canRun && (_jsx("div", { className: "card", style: { marginBottom: 12 }, children: _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }, children: [pipelines.length > 1 && (_jsxs("select", { value: pipelineId, onChange: (e) => setPipelineId(e.target.value === "" ? "" : Number(e.target.value)), style: { maxWidth: 320 }, children: [_jsxs("option", { value: "", children: ["Default", defaultPipeline ? `: ${defaultPipeline.display_name}` : ""] }), pipelines.map((p) => (_jsx("option", { value: p.id, children: p.display_name }, p.id)))] })), _jsx("button", { className: "primary", onClick: onRun, disabled: busy, children: busy ? "Starting…" : "Run validation pipeline" }), _jsx("span", { className: "muted", style: { fontSize: 13 }, children: "Runs against this request's validation environment." })] }) })), latest === undefined && _jsx("p", { className: "muted", children: "Loading\u2026" }), latest === null && (_jsxs("div", { className: "empty", children: ["No validation runs yet.", canRun
                        ? " Run a pipeline to collect evidence before approval."
                        : " A reviewer can run a pipeline to collect evidence."] })), latest && _jsx(RunView, { run: latest })] }));
}
function RunView({ run }) {
    const summary = run.summary_json ?? {};
    const stepCounts = (summary.stepStatusCounts ?? {});
    const countsText = Object.entries(stepCounts)
        .map(([k, v]) => `${v} ${k}`)
        .join(", ");
    return (_jsxs("div", { className: "card", children: [_jsxs("div", { className: "run-header", children: [_jsxs("div", { children: [_jsx("div", { className: "run-pipeline-name", children: run.pipeline_name }), _jsxs("div", { className: "muted", style: { fontSize: 12 }, children: ["v", run.pipeline_version, " \u00B7 started ", new Date(run.started_at).toLocaleString()] })] }), _jsxs("div", { style: { display: "flex", gap: 6, alignItems: "center" }, children: [_jsx("span", { className: `val-badge val-status-${run.status}`, children: RUN_STATUS_LABEL[run.status] }), _jsxs("span", { className: `val-badge val-impact-${run.approval_impact}`, children: ["Approval: ", IMPACT_LABEL[run.approval_impact]] })] })] }), countsText && (_jsxs("p", { className: "muted", style: { fontSize: 13, margin: "4px 0 12px" }, children: ["Checks: ", countsText] })), run.error_message && (_jsx("pre", { className: "error", style: { whiteSpace: "pre-wrap" }, children: run.error_message })), _jsx("div", { className: "step-cards", children: run.step_results.map((s) => (_jsx(StepResultCard, { step: s }, s.id))) })] }));
}
