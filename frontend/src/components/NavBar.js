import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { UserMenu } from "./UserMenu";
export function NavBar() {
    const { user } = useAuth();
    const isAdmin = user?.role === "admin";
    return (_jsxs("nav", { className: "nav", children: [_jsxs(NavLink, { to: "/requests", className: "brand", "aria-label": "Foyre home", children: [_jsx("img", { src: "/foyre-logo.png", alt: "", className: "brand-logo", "aria-hidden": "true" }), _jsx("span", { className: "brand-text", children: "Foyre" })] }), _jsxs("div", { className: "nav-links", children: [_jsx(NavLink, { to: "/requests", className: ({ isActive }) => isActive ? "nav-link is-active" : "nav-link", children: "Requests" }), isAdmin && (_jsx(NavLink, { to: "/admin", className: ({ isActive }) => isActive ? "nav-link is-active" : "nav-link", children: "Administration" }))] }), _jsx("span", { className: "spacer" }), _jsx(UserMenu, {})] }));
}
