import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { FormField } from "../../components/FormField";
function isVisible(field, values) {
    if (!field.visible_if)
        return true;
    return Object.entries(field.visible_if).every(([k, v]) => values[k] === v);
}
/**
 * Renders the live form using the exact same `<FormField />` component
 * requesters will see. Values are kept locally so the admin can play with
 * dropdowns / toggles without touching anything that gets saved.
 */
export function FormPreview({ sections }) {
    const [values, setValues] = useState({});
    if (sections.length === 0) {
        return (_jsx("p", { className: "muted", style: { padding: 12 }, children: "Add a section to see a preview of the form." }));
    }
    return (_jsx("div", { children: sections.map((section) => (_jsxs("fieldset", { className: "form-section", children: [_jsx("legend", { children: section.title || "(untitled section)" }), section.fields.length === 0 ? (_jsx("p", { className: "muted", style: { margin: 0 }, children: "No fields yet." })) : (section.fields
                    .filter((f) => isVisible(f, values))
                    .map((f) => (_jsx(FormField, { field: f, value: values[f.name], onChange: (v) => setValues((prev) => ({ ...prev, [f.name]: v })) }, f._key))))] }, section._key))) }));
}
