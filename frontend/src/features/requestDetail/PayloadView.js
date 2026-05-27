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
 *
 * If the request payload carries keys that don't appear in the current
 * schema (e.g. an admin removed a custom field after the request was
 * created), we surface them under "Other answers" so the data isn't
 * silently dropped from the UI.
 */
export function PayloadView({ schema, payload }) {
    const knownNames = new Set();
    for (const s of schema.sections) {
        for (const f of s.fields)
            knownNames.add(f.name);
    }
    const orphanEntries = Object.entries(payload).filter(([k]) => !knownNames.has(k));
    return (_jsxs("div", { children: [schema.sections.map((section) => (_jsxs("div", { className: "payload-section", children: [_jsx("h4", { children: section.title }), _jsx("dl", { children: section.fields.map((f) => {
                            const { text, unset } = formatValue(payload[f.name]);
                            return (_jsxs("div", { style: { display: "contents" }, children: [_jsx("dt", { children: f.label }), _jsx("dd", { className: unset ? "unset" : undefined, children: text })] }, f.name));
                        }) })] }, section.id))), orphanEntries.length > 0 && (_jsxs("div", { className: "payload-section", children: [_jsx("h4", { title: "These answers were captured under field names that are no longer part of the intake form. Likely the admin removed the field after this request was created.", children: "Other answers (no longer in form)" }), _jsx("dl", { children: orphanEntries.map(([k, v]) => {
                            const { text, unset } = formatValue(v);
                            return (_jsxs("div", { style: { display: "contents" }, children: [_jsx("dt", { children: _jsx("code", { children: k }) }), _jsx("dd", { className: unset ? "unset" : undefined, children: text })] }, k));
                        }) })] }))] }));
}
