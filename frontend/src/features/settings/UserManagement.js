import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { createUser, listUsers, updateUser } from "../../api/users";
import { useAuth } from "../../auth/useAuth";
import { generateTempPassword } from "./generateTempPassword";
import { NewUserCallout } from "./NewUserCallout";
import { RoleLegend } from "./RoleLegend";
import { ALL_ROLES_TOOLTIP, ROLE_DESCRIPTIONS, ROLE_ORDER, } from "./roleDescriptions";
export function UserManagement() {
    const { user: current } = useAuth();
    const [users, setUsers] = useState(null);
    const [error, setError] = useState(null);
    const [flash, setFlash] = useState(null);
    const [showCreate, setShowCreate] = useState(false);
    const [newUser, setNewUser] = useState(null);
    const reload = async () => {
        try {
            setUsers(await listUsers());
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
    };
    useEffect(() => {
        reload();
    }, []);
    const guarded = async (fn, successMsg) => {
        setError(null);
        setFlash(null);
        try {
            await fn();
            if (successMsg)
                setFlash(successMsg);
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
    };
    const confirmDeactivate = (u, targetActive) => {
        if (!targetActive) {
            return window.confirm(`Deactivate "${u.username}"?\n\n` +
                `They will no longer be able to log in. Their past requests, ` +
                `comments, and history entries are preserved. You can reactivate ` +
                `them at any time.`);
        }
        return true;
    };
    return (_jsxs("div", { children: [error && _jsx("div", { className: "error", children: error }), flash && (_jsx("div", { className: "muted", style: { marginBottom: 12 }, children: flash })), newUser && (_jsx(NewUserCallout, { info: newUser, onDismiss: () => setNewUser(null) })), _jsx("div", { className: "form-actions", style: { marginBottom: 12 }, children: !showCreate && (_jsx("button", { className: "primary", onClick: () => setShowCreate(true), children: "Create user" })) }), showCreate && (_jsx(CreateUserForm, { onCreated: (info) => {
                    setShowCreate(false);
                    setNewUser(info);
                    guarded(reload);
                }, onCancel: () => setShowCreate(false) })), _jsx("h4", { style: { marginTop: 24, marginBottom: 4 }, children: "Existing users" }), _jsxs("p", { className: "muted", style: { marginTop: 0, marginBottom: 12 }, children: ["Users aren't hard-deleted \u2014 they're ", _jsx("strong", { children: "deactivated" }), " so their history stays intact. Deactivated users can't log in; you can reactivate anytime."] }), _jsx(RoleLegend, {}), users === null ? (_jsx("p", { className: "muted", children: "Loading\u2026" })) : (_jsxs("table", { className: "data", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: { width: 64 }, children: "ID" }), _jsx("th", { children: "Username" }), _jsx("th", { children: "Email" }), _jsxs("th", { title: ALL_ROLES_TOOLTIP, style: { cursor: "help" }, children: ["Role ", _jsx("span", { "aria-hidden": true, children: "\u24D8" })] }), _jsx("th", { children: "Status" }), _jsx("th", { children: "Created" }), _jsx("th", { style: { width: 140 } })] }) }), _jsx("tbody", { children: users.map((u) => {
                            const isSelf = current?.id === u.id;
                            return (_jsxs("tr", { style: { opacity: u.is_active ? 1 : 0.55 }, children: [_jsxs("td", { children: ["#", u.id] }), _jsxs("td", { children: [u.username, isSelf && _jsx("span", { className: "muted", children: " (you)" }), u.must_change_password && (_jsx("span", { className: "muted", title: "This user has a temporary password and must change it on next login.", style: { marginLeft: 6 }, children: "\u00B7 temp pw" }))] }), _jsx("td", { className: "muted", children: u.email }), _jsx("td", { children: _jsx("select", { value: u.role, disabled: isSelf, onChange: (e) => guarded(async () => {
                                                await updateUser(u.id, {
                                                    role: e.target.value,
                                                });
                                                await reload();
                                            }), title: isSelf
                                                ? "Admins can't change their own role"
                                                : ROLE_DESCRIPTIONS[u.role].short, children: ROLE_ORDER.map((r) => (_jsx("option", { value: r, title: ROLE_DESCRIPTIONS[r].short, children: ROLE_DESCRIPTIONS[r].label }, r))) }) }), _jsx("td", { children: u.is_active ? (_jsx("span", { className: "badge", "data-status": "approved", children: "Active" })) : (_jsx("span", { className: "badge", "data-status": "rejected", children: "Deactivated" })) }), _jsx("td", { className: "muted", children: new Date(u.created_at).toLocaleDateString() }), _jsx("td", { children: isSelf ? (_jsx("span", { className: "muted", style: { fontSize: 12 }, children: "\u2014" })) : u.is_active ? (_jsx("button", { onClick: () => guarded(async () => {
                                                if (!confirmDeactivate(u, false))
                                                    return;
                                                await updateUser(u.id, { is_active: false });
                                                await reload();
                                            }, `${u.username} deactivated.`), children: "Deactivate" })) : (_jsx("button", { onClick: () => guarded(async () => {
                                                await updateUser(u.id, { is_active: true });
                                                await reload();
                                            }, `${u.username} reactivated.`), children: "Reactivate" })) })] }, u.id));
                        }) })] }))] }));
}
function CreateUserForm({ onCreated, onCancel, }) {
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    // Prefill with a strong generated temp password. Admin can regenerate or
    // type their own. The field stays `type="text"` so they can see / copy it.
    const [password, setPassword] = useState(() => generateTempPassword());
    const [role, setRole] = useState("requester");
    const [mustChange, setMustChange] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const onSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setBusy(true);
        try {
            await createUser({
                username,
                email,
                password,
                role,
                must_change_password: mustChange,
            });
            // Bubble up BEFORE resetting so the callout can render the password.
            onCreated({
                username,
                tempPassword: password,
                mustChangeOnLogin: mustChange,
            });
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs("div", { className: "card", style: { marginBottom: 16 }, children: [_jsx("h4", { style: { marginTop: 0, marginBottom: 4 }, children: "Create user" }), _jsx("p", { className: "muted", style: { marginTop: 0, marginBottom: 12 }, children: "A strong temporary password has been generated below. You'll see it again after creating the user so you can share it out-of-band. If the box is checked, the user must change it on first login." }), error && _jsx("div", { className: "error", children: error }), _jsxs("form", { onSubmit: onSubmit, style: {
                    display: "grid",
                    gridTemplateColumns: "repeat(2, 1fr)",
                    gap: 12,
                }, children: [_jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "Username" }), _jsx("input", { value: username, onChange: (e) => setUsername(e.target.value), required: true, autoComplete: "off" })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "Email" }), _jsx("input", { type: "email", value: email, onChange: (e) => setEmail(e.target.value), required: true, autoComplete: "off" })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", children: "Temporary password" }), _jsxs("div", { style: { display: "flex", gap: 6 }, children: [_jsx("input", { type: "text", value: password, onChange: (e) => setPassword(e.target.value), required: true, minLength: 8, autoComplete: "off", style: {
                                            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                                        } }), _jsx("button", { type: "button", onClick: () => setPassword(generateTempPassword()), title: "Generate a new random password", children: "Regenerate" })] })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsxs("span", { className: "label", title: ALL_ROLES_TOOLTIP, style: { cursor: "help" }, children: ["Role", " ", _jsx("span", { "aria-hidden": true, style: { color: "var(--muted)", fontWeight: 400 }, children: "\u24D8" })] }), _jsx("select", { value: role, onChange: (e) => setRole(e.target.value), title: ROLE_DESCRIPTIONS[role].short, children: ROLE_ORDER.map((r) => (_jsx("option", { value: r, title: ROLE_DESCRIPTIONS[r].short, children: ROLE_DESCRIPTIONS[r].label }, r))) }), _jsx("span", { className: "muted", style: { fontSize: 12, marginTop: 4, display: "block" }, children: ROLE_DESCRIPTIONS[role].short })] }), _jsxs("label", { style: {
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            gridColumn: "1 / -1",
                        }, children: [_jsx("input", { type: "checkbox", checked: mustChange, onChange: (e) => setMustChange(e.target.checked), style: { width: "auto" } }), _jsx("span", { children: "Require user to change this password on first login" })] }), _jsxs("div", { className: "form-actions", style: { gridColumn: "1 / -1", marginTop: 0 }, children: [_jsx("button", { type: "submit", className: "primary", disabled: busy, children: busy ? "Creating…" : "Create user" }), _jsx("button", { type: "button", onClick: onCancel, disabled: busy, children: "Cancel" })] })] })] }));
}
