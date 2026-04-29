import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { PasswordForm } from "../features/settings/PasswordForm";
/**
 * Shown (and required) when `user.must_change_password` is true — e.g. the
 * first time a user logs in with an admin-provided temporary password. Uses a
 * standalone layout so it's visually clear this is a gate, not a normal page.
 */
export function ForcePasswordChangePage() {
    const { user, loading } = useAuth();
    if (loading)
        return _jsx("div", { className: "login-wrap muted", children: "Loading\u2026" });
    if (!user)
        return _jsx(Navigate, { to: "/login", replace: true });
    // If the flag already isn't set, there's nothing to do here.
    if (!user.must_change_password)
        return _jsx(Navigate, { to: "/requests", replace: true });
    return (_jsxs("div", { className: "login-wrap", children: [_jsx("h1", { children: "Set a new password" }), _jsxs("p", { className: "muted", style: { marginBottom: 16 }, children: ["You're signed in as ", _jsx("strong", { children: user.username }), ". Please replace your temporary password before continuing."] }), _jsx("div", { className: "card", children: _jsx(PasswordForm, { primaryLabel: "Set new password" }) })] }));
}
