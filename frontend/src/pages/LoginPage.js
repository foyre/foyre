import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
export function LoginPage() {
    const { user, loading, login } = useAuth();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    if (loading) {
        return _jsx("div", { className: "login-wrap muted", children: "Loading\u2026" });
    }
    if (user)
        return _jsx(Navigate, { to: "/requests", replace: true });
    const onSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setBusy(true);
        try {
            await login(username, password);
        }
        catch (err) {
            setError(err instanceof Error && err.message.startsWith("401")
                ? "Invalid username or password."
                : "Login failed. Please try again.");
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs("div", { className: "login-wrap", children: [_jsxs("div", { className: "login-brand", children: [_jsx("img", { src: "/foyre-logo.png", alt: "", "aria-hidden": "true" }), _jsx("h1", { children: "Foyre" })] }), _jsx("div", { className: "card", children: _jsxs("form", { onSubmit: onSubmit, children: [error && _jsx("div", { className: "error", children: error }), _jsxs("label", { className: "field", children: [_jsx("span", { className: "label", children: "Username" }), _jsx("input", { value: username, onChange: (e) => setUsername(e.target.value), autoFocus: true, autoComplete: "username", required: true })] }), _jsxs("label", { className: "field", children: [_jsx("span", { className: "label", children: "Password" }), _jsx("input", { type: "password", value: password, onChange: (e) => setPassword(e.target.value), autoComplete: "current-password", required: true })] }), _jsx("button", { type: "submit", className: "primary", disabled: busy, children: busy ? "Signing in…" : "Sign in" })] }) })] }));
}
