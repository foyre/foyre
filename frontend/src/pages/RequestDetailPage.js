import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiErrorMessage } from "../api/errors";
import { getFormSchema } from "../api/meta";
import { changeStatus, getRequest, submitRequest } from "../api/requests";
import { useAuth } from "../auth/useAuth";
import { RiskBadge } from "../components/RiskBadge";
import { StatusBadge } from "../components/StatusBadge";
import { CommentComposer } from "../features/comments/CommentComposer";
import { CommentList } from "../features/comments/CommentList";
import { HistoryList } from "../features/history/HistoryList";
import { PayloadView } from "../features/requestDetail/PayloadView";
import { availableTransitions } from "../features/requestActions";
import { ValidationEnvCard } from "../features/validation/ValidationEnvCard";
import { isPrivileged, } from "../types/domain";
export function RequestDetailPage() {
    const { id } = useParams();
    const reqId = Number(id);
    const { user } = useAuth();
    const [req, setReq] = useState(null);
    const [schema, setSchema] = useState(null);
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    const [reloadKey, setReloadKey] = useState(0);
    useEffect(() => {
        Promise.all([getRequest(reqId), getFormSchema()])
            .then(([r, s]) => {
            setReq(r);
            setSchema(s);
        })
            .catch((e) => setError(apiErrorMessage(e)));
    }, [reqId]);
    if (error)
        return _jsx("div", { className: "error", children: error });
    if (!req || !schema || !user)
        return _jsx("p", { className: "muted", children: "Loading\u2026" });
    const isOwner = req.created_by_id === user.id;
    const canReview = isPrivileged(user.role);
    const canComment = canReview;
    const actions = availableTransitions(req.status, user.role);
    const runAction = async (fn) => {
        setBusy(true);
        setError(null);
        try {
            const updated = await fn();
            setReq(updated);
            setReloadKey((k) => k + 1);
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    const appName = req.payload.application_name ||
        "(untitled)";
    return (_jsxs("section", { children: [_jsxs("div", { className: "header-row", children: [_jsxs("div", { children: [_jsxs("h2", { style: { marginBottom: 4 }, children: [appName, " ", _jsxs("span", { className: "muted", style: { fontWeight: 400 }, children: ["#", req.id] })] }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center" }, children: [_jsx(StatusBadge, { status: req.status }), _jsx(RiskBadge, { level: req.risk_level })] })] }), isOwner && req.status === "draft" && (_jsx(Link, { to: `/requests/${req.id}/edit`, children: _jsx("button", { children: "Edit draft" }) }))] }), _jsxs("dl", { className: "meta", children: [_jsx("dt", { children: "Requester" }), _jsxs("dd", { children: [req.created_by?.username ?? `#${req.created_by_id}`, req.created_by && (_jsxs("span", { className: "muted", children: [" \u00B7 ", req.created_by.role] }))] }), _jsx("dt", { children: "Created" }), _jsx("dd", { children: new Date(req.created_at).toLocaleString() }), _jsx("dt", { children: "Updated" }), _jsx("dd", { children: new Date(req.updated_at).toLocaleString() })] }), req.risk_reasons && req.risk_reasons.length > 0 && (_jsxs("div", { className: "payload-section", children: [_jsx("h4", { children: "Risk reasons" }), _jsx("div", { style: { padding: "12px 14px" }, children: _jsx("ul", { style: { margin: 0, paddingLeft: 20 }, children: req.risk_reasons.map((r, i) => (_jsx("li", { children: r }, i))) }) })] })), isOwner && req.status === "draft" && (_jsx("div", { className: "form-actions", style: { marginBottom: 16 }, children: _jsx("button", { className: "primary", disabled: busy, onClick: () => runAction(() => submitRequest(req.id)), children: "Submit for review" }) })), (isOwner || user.role === "admin") && req.status === "submitted" && (_jsxs("div", { className: "form-actions", style: { marginBottom: 16 }, children: [_jsx("button", { className: "primary", disabled: busy, onClick: () => runAction(() => changeStatus(req.id, "ready_for_review")), children: "Mark ready for review" }), _jsx("span", { className: "muted", style: { fontSize: 13 }, children: "Signals to reviewers that you've deployed into your validation cluster and are ready for feedback." })] })), (isOwner || user.role === "admin") && req.status === "ready_for_review" && (_jsxs("div", { className: "form-actions", style: { marginBottom: 16 }, children: [_jsx("button", { disabled: busy, onClick: () => runAction(() => changeStatus(req.id, "submitted")), children: "Move back to submitted" }), _jsx("span", { className: "muted", style: { fontSize: 13 }, children: "Use this if you need to keep working before reviewers look." })] })), canReview && actions.length > 0 && (_jsx("div", { className: "form-actions", style: { marginBottom: 16 }, children: actions.map((a) => (_jsx("button", { className: a.kind === "primary" ? "primary" : undefined, disabled: busy, onClick: () => runAction(() => changeStatus(req.id, a.to)), children: a.label }, a.to))) })), _jsxs("div", { className: "section-block", children: [_jsx("h3", { children: "Request details" }), _jsx(PayloadView, { schema: schema, payload: req.payload })] }), (isOwner || user.role === "admin") && (_jsx(ValidationEnvCard, { request: req, onEnvChanged: () => setReloadKey((k) => k + 1) })), _jsxs("div", { className: "section-block", children: [_jsx("h3", { children: "Comments" }), _jsx(CommentList, { requestId: req.id, reloadKey: reloadKey }), canComment && (_jsx(CommentComposer, { requestId: req.id, onPosted: () => setReloadKey((k) => k + 1) }))] }), _jsxs("div", { className: "section-block", children: [_jsx("h3", { children: "History" }), _jsx(HistoryList, { requestId: req.id, reloadKey: reloadKey })] })] }));
}
