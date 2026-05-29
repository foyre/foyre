import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { getHistory } from "../../api/requests";
const EVENT_LABELS = {
    created: "Created",
    updated: "Updated",
    submitted: "Submitted",
    status_changed: "Status changed",
    commented: "Commented",
    risk_evaluated: "Risk evaluated",
    validation_env_requested: "Validation environment requested",
    validation_env_ready: "Validation environment ready",
    validation_env_failed: "Validation environment failed",
    validation_env_torn_down: "Validation environment torn down",
    validation_run_started: "Validation run started",
    validation_run_completed: "Validation run completed",
    validation_run_failed: "Validation run failed",
    validation_approval_blocked: "Approval blocked by validation",
    validation_override_used: "Validation override used",
    validation_artifact_created: "Validation artifact created",
};
function describe(e) {
    if (!e.detail)
        return null;
    if (e.event_type === "status_changed") {
        const d = e.detail;
        return `${d.from} → ${d.to}`;
    }
    if (e.event_type === "risk_evaluated") {
        const d = e.detail;
        const reasons = d.reasons?.length ? ` (${d.reasons.join("; ")})` : "";
        return `${d.level}${reasons}`;
    }
    if (e.event_type === "validation_run_completed") {
        const d = e.detail;
        return `${d.pipeline}: ${d.status} (approval: ${d.approval_impact})`;
    }
    if (e.event_type === "validation_run_started") {
        const d = e.detail;
        return d.pipeline ?? null;
    }
    if (e.event_type === "validation_override_used" ||
        e.event_type === "validation_approval_blocked") {
        const d = e.detail;
        return d.reason ?? null;
    }
    return null;
}
export function HistoryList({ requestId, reloadKey = 0, }) {
    const [items, setItems] = useState(null);
    useEffect(() => {
        getHistory(requestId).then(setItems);
    }, [requestId, reloadKey]);
    if (items === null)
        return _jsx("p", { className: "muted", children: "Loading\u2026" });
    if (items.length === 0)
        return _jsx("p", { className: "muted", children: "No history yet." });
    return (_jsx("ul", { className: "history-list", children: items.map((e) => {
            const desc = describe(e);
            return (_jsxs("li", { children: [_jsxs("div", { className: "meta-row", children: [_jsx("strong", { children: EVENT_LABELS[e.event_type] ?? e.event_type }), _jsxs("span", { className: "muted", children: [" · ", e.actor?.username ?? `user #${e.actor_id}`, " · ", new Date(e.created_at).toLocaleString()] })] }), desc && _jsx("code", { children: desc })] }, e.id));
        }) }));
}
