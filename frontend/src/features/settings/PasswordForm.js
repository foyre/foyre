import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { changeMyPassword } from "../../api/users";
import { useAuth } from "../../auth/useAuth";
export function PasswordForm({ onSuccess, secondaryAction, primaryLabel = "Change password", }) {
    const { refreshUser } = useAuth();
    const [current, setCurrent] = useState("");
    const [next, setNext] = useState("");
    const [confirm, setConfirm] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [flash, setFlash] = useState(null);
    const reset = () => {
        setCurrent("");
        setNext("");
        setConfirm("");
    };
    const onSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setFlash(null);
        if (next.length < 8) {
            setError("New password must be at least 8 characters.");
            return;
        }
        if (next !== confirm) {
            setError("New password and confirmation don't match.");
            return;
        }
        setBusy(true);
        try {
            await changeMyPassword(current, next);
            await refreshUser();
            reset();
            setFlash("Password updated.");
            onSuccess?.();
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs("form", { onSubmit: onSubmit, style: { maxWidth: 420 }, children: [error && _jsx("div", { className: "error", children: error }), _jsxs("label", { className: "field", children: [_jsx("span", { className: "label", children: "Current password" }), _jsx("input", { type: "password", value: current, onChange: (e) => setCurrent(e.target.value), autoComplete: "current-password", required: true })] }), _jsxs("label", { className: "field", children: [_jsx("span", { className: "label", children: "New password" }), _jsx("input", { type: "password", value: next, onChange: (e) => setNext(e.target.value), autoComplete: "new-password", required: true, minLength: 8 })] }), _jsxs("label", { className: "field", children: [_jsx("span", { className: "label", children: "Confirm new password" }), _jsx("input", { type: "password", value: confirm, onChange: (e) => setConfirm(e.target.value), autoComplete: "new-password", required: true, minLength: 8 })] }), _jsxs("div", { className: "form-actions", children: [_jsx("button", { className: "primary", type: "submit", disabled: busy, children: busy ? "Updating…" : primaryLabel }), secondaryAction, flash && _jsx("span", { className: "flash", children: flash })] })] }));
}
