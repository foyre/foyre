import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useAuth } from "../auth/useAuth";
import { PasswordForm } from "../features/settings/PasswordForm";
import { ROLE_DESCRIPTIONS } from "../features/settings/roleDescriptions";
/**
 * Personal account page. Anything account-specific lives here: profile info,
 * password change, and (eventually) personal preferences. System-wide / admin
 * settings live under /admin.
 */
export function AccountPage() {
    const { user } = useAuth();
    const [showPasswordForm, setShowPasswordForm] = useState(false);
    if (!user)
        return null;
    return (_jsxs("section", { children: [_jsx("div", { className: "header-row", children: _jsx("h2", { children: "Your account" }) }), _jsx("div", { className: "card", children: _jsxs("dl", { className: "meta", style: { marginBottom: 0 }, children: [_jsx("dt", { children: "Username" }), _jsx("dd", { children: user.username }), _jsx("dt", { children: "Email" }), _jsx("dd", { children: user.email }), _jsx("dt", { children: "Role" }), _jsxs("dd", { title: ROLE_DESCRIPTIONS[user.role].short, style: { cursor: "help" }, children: [ROLE_DESCRIPTIONS[user.role].label, " ", _jsxs("span", { className: "muted", style: { fontSize: 12 }, children: ["\u2014 ", ROLE_DESCRIPTIONS[user.role].short] })] }), _jsx("dt", { children: "Password" }), _jsx("dd", { children: !showPasswordForm ? (_jsx("button", { onClick: () => setShowPasswordForm(true), children: "Change password" })) : (_jsx("div", { style: { marginTop: 4 }, children: _jsx(PasswordForm, { onSuccess: () => setShowPasswordForm(false), secondaryAction: _jsx("button", { type: "button", onClick: () => setShowPasswordForm(false), children: "Cancel" }) }) })) })] }) })] }));
}
