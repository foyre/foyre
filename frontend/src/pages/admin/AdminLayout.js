import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { NavLink, Outlet } from "react-router-dom";
/**
 * Admin area shell. Horizontal tabs at the top; the active tab renders via
 * <Outlet /> in the panel below. Add future admin surfaces (auth providers,
 * policy rules, etc.) as new tabs here.
 */
export function AdminLayout() {
    return (_jsxs("section", { children: [_jsx("div", { className: "header-row", children: _jsx("h2", { children: "Administration" }) }), _jsxs("div", { className: "admin-tabs", role: "tablist", "aria-label": "Administration sections", children: [_jsx(NavLink, { to: "/admin/users", role: "tab", className: ({ isActive }) => isActive ? "admin-tab is-active" : "admin-tab", children: "Users" }), _jsx(NavLink, { to: "/admin/validation-environments", role: "tab", className: ({ isActive }) => isActive ? "admin-tab is-active" : "admin-tab", children: "Validation environments" })] }), _jsx("div", { className: "admin-panel", children: _jsx(Outlet, {}) })] }));
}
