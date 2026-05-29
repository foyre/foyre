import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { changeStatus } from "../../api/requests";
import { getApprovalGate } from "../../api/validationRuns";
/**
 * Approve button that respects the validation approval gate. If the latest
 * validation run blocks approval, it opens a modal: either an override form
 * (when policy allows) or an explanation that approval can't proceed.
 */
export function ApproveControl({ request: req, reloadKey, onApproved }) {
    const [gate, setGate] = useState(null);
    const [modalOpen, setModalOpen] = useState(false);
    const [reason, setReason] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    useEffect(() => {
        getApprovalGate(req.id)
            .then(setGate)
            .catch(() => setGate(null));
    }, [req.id, reloadKey]);
    const doApprove = async (override) => {
        setBusy(true);
        setError(null);
        try {
            const updated = await changeStatus(req.id, "approved", {
                override_validation: override ? true : undefined,
                override_reason: override?.reason,
            });
            setModalOpen(false);
            onApproved(updated);
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    const onClick = () => {
        setError(null);
        if (gate?.blocked) {
            setModalOpen(true);
        }
        else {
            void doApprove();
        }
    };
    return (_jsxs(_Fragment, { children: [_jsx("button", { className: "primary", onClick: onClick, disabled: busy, children: gate?.blocked ? "Approve (blocked)" : "Approve" }), gate && !gate.blocked && gate.impact === "warning" && (_jsx("span", { className: "muted", style: { fontSize: 13 }, children: "\u26A0 Validation finished with warnings \u2014 review before approving." })), gate && !gate.blocked && gate.missing_validation && (_jsx("span", { className: "muted", style: { fontSize: 13 }, children: "No validation run yet \u2014 consider running one first." })), modalOpen && gate && (_jsx("div", { className: "modal-overlay", role: "dialog", "aria-modal": "true", children: _jsxs("div", { className: "modal", children: [_jsx("h3", { style: { marginTop: 0 }, children: "Approval blocked by validation" }), _jsx("p", { children: gate.reason }), error && _jsx("div", { className: "error", children: error }), gate.override_allowed ? (_jsxs(_Fragment, { children: [_jsxs("label", { className: "field", children: [_jsx("span", { className: "label", children: "Override reason (required)" }), _jsx("textarea", { value: reason, onChange: (e) => setReason(e.target.value), rows: 3, placeholder: "e.g. Critical CVE has no fix yet; compensating controls in place. Approved by security lead." })] }), _jsxs("div", { className: "form-actions", children: [_jsx("button", { className: "primary", disabled: busy || !reason.trim(), onClick: () => doApprove({ reason: reason.trim() }), children: busy ? "Approving…" : "Override and approve" }), _jsx("button", { onClick: () => setModalOpen(false), disabled: busy, children: "Cancel" })] })] })) : (_jsxs(_Fragment, { children: [_jsx("p", { className: "muted", children: "Overriding a blocked approval is disabled by policy. Resolve the blocking findings and re-run validation." }), _jsx("div", { className: "form-actions", children: _jsx("button", { onClick: () => setModalOpen(false), children: "Close" }) })] }))] }) }))] }));
}
