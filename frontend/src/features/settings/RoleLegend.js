import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useState } from "react";
import { ROLE_DESCRIPTIONS, ROLE_ORDER } from "./roleDescriptions";
export function RoleLegend() {
    const [open, setOpen] = useState(false);
    return (_jsxs("div", { className: "card", style: { marginBottom: 16, padding: "12px 16px" }, children: [_jsxs("button", { type: "button", onClick: () => setOpen((v) => !v), "aria-expanded": open, style: {
                    background: "transparent",
                    border: "none",
                    padding: 0,
                    cursor: "pointer",
                    color: "var(--accent)",
                    fontWeight: 500,
                }, children: [open ? "\u25BE" : "\u25B8", " What can each role do?"] }), open && (_jsx("dl", { style: {
                    display: "grid",
                    gridTemplateColumns: "max-content 1fr",
                    gap: "10px 16px",
                    margin: "12px 0 0",
                }, children: ROLE_ORDER.map((r) => {
                    const info = ROLE_DESCRIPTIONS[r];
                    return (_jsxs("div", { style: { display: "contents" }, children: [_jsx("dt", { style: { fontWeight: 500 }, children: info.label }), _jsx("dd", { style: { margin: 0 }, children: _jsx("ul", { style: { margin: 0, paddingLeft: 18 }, children: info.bullets.map((b, i) => (_jsx("li", { children: b }, i))) }) })] }, r));
                }) }))] }));
}
