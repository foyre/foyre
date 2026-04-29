import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/useAuth";
import { Layout } from "./components/Layout";
import { AccountPage } from "./pages/AccountPage";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { AdminUsersPage } from "./pages/admin/AdminUsersPage";
import { AdminValidationEnvironmentsPage } from "./pages/admin/AdminValidationEnvironmentsPage";
import { ForcePasswordChangePage } from "./pages/ForcePasswordChangePage";
import { LoginPage } from "./pages/LoginPage";
import { RequestDetailPage } from "./pages/RequestDetailPage";
import { RequestEditPage } from "./pages/RequestEditPage";
import { RequestNewPage } from "./pages/RequestNewPage";
import { RequestsListPage } from "./pages/RequestsListPage";
function RequireAuth({ children }) {
    const { user, loading } = useAuth();
    const location = useLocation();
    if (loading)
        return _jsx("div", { className: "page muted", children: "Loading\u2026" });
    if (!user)
        return _jsx(Navigate, { to: "/login", replace: true });
    if (user.must_change_password && location.pathname !== "/change-password") {
        return _jsx(Navigate, { to: "/change-password", replace: true });
    }
    return _jsx(_Fragment, { children: children });
}
function RequireAdmin({ children }) {
    const { user, loading } = useAuth();
    if (loading)
        return _jsx("div", { className: "page muted", children: "Loading\u2026" });
    if (!user)
        return _jsx(Navigate, { to: "/login", replace: true });
    if (user.role !== "admin")
        return _jsx(Navigate, { to: "/requests", replace: true });
    return _jsx(_Fragment, { children: children });
}
export function AppRouter() {
    return (_jsxs(Routes, { children: [_jsx(Route, { path: "/login", element: _jsx(LoginPage, {}) }), _jsx(Route, { path: "/change-password", element: _jsx(RequireAuth, { children: _jsx(ForcePasswordChangePage, {}) }) }), _jsxs(Route, { element: _jsx(RequireAuth, { children: _jsx(Layout, {}) }), children: [_jsx(Route, { path: "/", element: _jsx(Navigate, { to: "/requests", replace: true }) }), _jsx(Route, { path: "/requests", element: _jsx(RequestsListPage, {}) }), _jsx(Route, { path: "/requests/new", element: _jsx(RequestNewPage, {}) }), _jsx(Route, { path: "/requests/:id", element: _jsx(RequestDetailPage, {}) }), _jsx(Route, { path: "/requests/:id/edit", element: _jsx(RequestEditPage, {}) }), _jsx(Route, { path: "/account", element: _jsx(AccountPage, {}) }), _jsx(Route, { path: "/settings", element: _jsx(Navigate, { to: "/account", replace: true }) }), _jsxs(Route, { path: "/admin", element: _jsx(RequireAdmin, { children: _jsx(AdminLayout, {}) }), children: [_jsx(Route, { index: true, element: _jsx(Navigate, { to: "users", replace: true }) }), _jsx(Route, { path: "users", element: _jsx(AdminUsersPage, {}) }), _jsx(Route, { path: "validation-environments", element: _jsx(AdminValidationEnvironmentsPage, {}) })] })] })] }));
}
