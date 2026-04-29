import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
/**
 * Dropdown anchored to the current username in the nav.
 *
 * Accessibility:
 *   - Trigger is a real <button> with aria-haspopup="menu", aria-expanded.
 *   - Menu is a <div role="menu"> with role="menuitem" children.
 *   - ESC closes, outside click closes, selecting any item closes.
 */
export function UserMenu() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const rootRef = useRef(null);
    useEffect(() => {
        if (!open)
            return;
        const onDocClick = (e) => {
            if (!rootRef.current)
                return;
            if (e.target instanceof Node && !rootRef.current.contains(e.target)) {
                setOpen(false);
            }
        };
        const onKey = (e) => {
            if (e.key === "Escape")
                setOpen(false);
        };
        document.addEventListener("mousedown", onDocClick);
        document.addEventListener("keydown", onKey);
        return () => {
            document.removeEventListener("mousedown", onDocClick);
            document.removeEventListener("keydown", onKey);
        };
    }, [open]);
    if (!user)
        return null;
    const go = (path) => {
        setOpen(false);
        navigate(path);
    };
    const onSignOut = () => {
        setOpen(false);
        logout();
        navigate("/login", { replace: true });
    };
    const initials = (user.username || "?").slice(0, 2).toUpperCase();
    return (_jsxs("div", { className: "user-menu", ref: rootRef, children: [_jsxs("button", { type: "button", className: "user-menu-trigger", "aria-haspopup": "menu", "aria-expanded": open, onClick: () => setOpen((v) => !v), children: [_jsx("span", { className: "user-avatar", "aria-hidden": "true", children: initials }), _jsxs("span", { className: "user-menu-name", children: [user.username, _jsx("span", { className: "user-menu-role", children: user.role })] }), _jsx("span", { className: "user-menu-caret", "aria-hidden": "true", children: open ? "\u25B4" : "\u25BE" })] }), open && (_jsxs("div", { className: "user-menu-popover", role: "menu", children: [_jsxs("div", { className: "user-menu-identity", children: [_jsx("div", { className: "user-menu-identity-name", children: user.username }), _jsx("div", { className: "user-menu-identity-email", children: user.email }), _jsxs("div", { className: "user-menu-identity-role", children: ["Signed in as ", _jsx("strong", { children: user.role })] })] }), _jsx("div", { className: "user-menu-items", children: _jsx("button", { type: "button", role: "menuitem", className: "user-menu-item", onClick: () => go("/account"), children: "Your account" }) }), _jsx("div", { className: "user-menu-items user-menu-items-bottom", children: _jsx("button", { type: "button", role: "menuitem", className: "user-menu-item", onClick: onSignOut, children: "Sign out" }) })] }))] }));
}
