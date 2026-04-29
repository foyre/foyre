import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function FormField({ field, value, onChange, error }) {
    const id = `f-${field.name}`;
    const invalid = Boolean(error);
    const common = {
        id,
        name: field.name,
        "aria-invalid": invalid || undefined,
        "aria-describedby": error ? `${id}-err` : undefined,
    };
    const label = (_jsxs("span", { className: "label", children: [field.label, field.required && (_jsx("span", { className: "req", "aria-hidden": "true", children: "*" }))] }));
    const errorNode = error ? (_jsx("span", { id: `${id}-err`, className: "field-error", role: "alert", children: error })) : null;
    switch (field.type) {
        case "textarea":
            return (_jsxs("label", { className: "field", children: [label, _jsx("textarea", { ...common, value: value ?? "", onChange: (e) => onChange(e.target.value), rows: 4 }), errorNode] }));
        case "select":
            return (_jsxs("label", { className: "field", children: [label, _jsxs("select", { ...common, value: value ?? "", onChange: (e) => onChange(e.target.value), children: [_jsx("option", { value: "", children: "\u2014" }), field.options?.map((o) => (_jsx("option", { value: o.value, children: o.label }, o.value)))] }), errorNode] }));
        case "boolean":
            return (_jsxs("label", { className: "field", style: { display: "flex", alignItems: "center", gap: 8 }, children: [_jsx("input", { ...common, type: "checkbox", checked: Boolean(value), onChange: (e) => onChange(e.target.checked), style: { width: "auto" } }), _jsxs("span", { children: [field.label, field.required && (_jsx("span", { className: "req", "aria-hidden": "true", children: "*" }))] }), errorNode] }));
        default:
            return (_jsxs("label", { className: "field", children: [label, _jsx("input", { ...common, type: "text", value: value ?? "", onChange: (e) => onChange(e.target.value) }), errorNode] }));
    }
}
