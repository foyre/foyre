import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { getValidationPolicy, updateValidationPolicy, } from "../../api/validationPolicy";
const TOGGLES = [
    {
        key: "require_validation_before_approval",
        label: "Require a completed validation run before approval",
        help: "Blocks approval until at least one validation pipeline run has completed.",
    },
    {
        key: "block_approval_on_failed_validation",
        label: "Block approval when the latest run has blocking failures",
        help: "When on, a blocking failure must be resolved or overridden before approval.",
    },
    {
        key: "allow_validation_override",
        label: "Allow reviewers to override a blocked approval (with a reason)",
        help: "When off, a blocked approval cannot be overridden by anyone.",
    },
];
export function PolicyControls() {
    const [policy, setPolicy] = useState(null);
    const [error, setError] = useState(null);
    const [flash, setFlash] = useState(null);
    const [busyKey, setBusyKey] = useState(null);
    useEffect(() => {
        getValidationPolicy()
            .then(setPolicy)
            .catch((e) => setError(apiErrorMessage(e)));
    }, []);
    const toggle = async (key) => {
        if (!policy)
            return;
        setBusyKey(key);
        setError(null);
        setFlash(null);
        try {
            const updated = await updateValidationPolicy({ [key]: !policy[key] });
            setPolicy(updated);
            setFlash("Policy updated.");
        }
        catch (e) {
            setError(apiErrorMessage(e));
        }
        finally {
            setBusyKey(null);
        }
    };
    return (_jsxs("div", { className: "card", style: { marginBottom: 20 }, children: [_jsx("h4", { style: { marginTop: 0, marginBottom: 4 }, children: "Approval policy" }), _jsx("p", { className: "muted", style: { marginTop: 0, marginBottom: 12, fontSize: 13 }, children: "Controls how validation results gate the approval decision." }), error && _jsx("div", { className: "error", children: error }), flash && (_jsx("div", { className: "muted", style: { marginBottom: 8 }, children: flash })), policy === null ? (_jsx("p", { className: "muted", children: "Loading\u2026" })) : (_jsx("div", { className: "stack", children: TOGGLES.map((t) => (_jsxs("label", { className: "inline-toggle", style: { alignItems: "flex-start", gap: 10 }, children: [_jsx("input", { type: "checkbox", checked: policy[t.key], disabled: busyKey !== null, onChange: () => toggle(t.key), style: { marginTop: 3 } }), _jsxs("span", { children: [t.label, _jsx("span", { className: "muted", style: { display: "block", fontSize: 12, fontWeight: 400 }, children: t.help })] })] }, t.key))) }))] }));
}
