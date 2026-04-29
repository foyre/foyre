import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
function formatValue(v) {
    if (v === undefined || v === null || v === "")
        return { text: "—", unset: true };
    if (typeof v === "boolean")
        return { text: v ? "Yes" : "No", unset: false };
    return { text: String(v), unset: false };
}
/**
 * Read-only, section-grouped render of a payload using the form schema's
 * section/field layout. Fields missing from the payload render as "—" so
 * reviewers see what's unanswered vs. what's explicitly blank.
 */
export function PayloadView({ schema, payload }) {
    return (_jsx("div", { children: schema.sections.map((section) => (_jsxs("div", { className: "payload-section", children: [_jsx("h4", { children: section.title }), _jsx("dl", { children: section.fields.map((f) => {
                        const { text, unset } = formatValue(payload[f.name]);
                        return (_jsxs("div", { style: { display: "contents" }, children: [_jsx("dt", { children: f.label }), _jsx("dd", { className: unset ? "unset" : undefined, children: text })] }, f.name));
                    }) })] }, section.id))) }));
}
