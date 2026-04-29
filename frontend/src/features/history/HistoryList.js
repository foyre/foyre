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
