import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { UserManagement } from "../../features/settings/UserManagement";
export function AdminUsersPage() {
    return (_jsxs("div", { children: [_jsx("p", { className: "muted", style: { marginTop: 0, marginBottom: 12 }, children: "Create local users, manage roles, and deactivate accounts. You can't change your own role or deactivate yourself." }), _jsx(UserManagement, {})] }));
}
