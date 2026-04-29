import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";
export function Layout() {
    return (_jsxs(_Fragment, { children: [_jsx(NavBar, {}), _jsx("main", { className: "page", children: _jsx(Outlet, {}) })] }));
}
