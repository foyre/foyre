import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { FieldRow } from "./FieldRow";
import { suggestFieldName, uniqueKey, } from "./types";
export function SchemaSectionCard({ section, allSections, index, total, onPatch, onMoveUp, onMoveDown, onDelete, onPatchField, onDeleteField, onMoveFieldUp, onMoveFieldDown, onMoveFieldToSection, onAddField, }) {
    const [addOpen, setAddOpen] = useState(false);
    const hasCoreFields = section.fields.some((f) => f.source === "core");
    const canDelete = section.fields.length === 0 || !hasCoreFields;
    return (_jsxs("div", { className: "schema-section-card", children: [_jsxs("div", { className: "schema-section-header", children: [_jsxs("div", { className: "schema-section-reorder", children: [_jsx("button", { type: "button", className: "icon-btn", onClick: onMoveUp, disabled: index === 0, title: "Move section up", "aria-label": "Move section up", children: "\u2191" }), _jsx("button", { type: "button", className: "icon-btn", onClick: onMoveDown, disabled: index === total - 1, title: "Move section down", "aria-label": "Move section down", children: "\u2193" })] }), _jsx("input", { className: "schema-section-title-input", type: "text", value: section.title, onChange: (e) => onPatch({ title: e.target.value }), placeholder: "Section title" }), _jsx("button", { type: "button", onClick: onDelete, className: "danger-btn", disabled: !canDelete, title: !canDelete
                            ? "This section contains built-in fields. Move them elsewhere before deleting."
                            : "Delete this section", children: "Delete section" })] }), section.fields.length === 0 ? (_jsx("p", { className: "muted", style: { padding: "12px 14px", margin: 0 }, children: "No fields in this section yet. Add one below or move fields here from another section." })) : (_jsx("div", { className: "schema-fields-list", children: section.fields.map((f, i) => (_jsx(FieldRow, { field: f, sections: allSections, currentSectionId: section.id, canMoveUp: i > 0, canMoveDown: i < section.fields.length - 1, onPatch: (patch) => onPatchField(f._key, patch), onMoveUp: () => onMoveFieldUp(f._key), onMoveDown: () => onMoveFieldDown(f._key), onDelete: () => onDeleteField(f._key), onMoveToSection: (sid) => onMoveFieldToSection(f._key, sid) }, f._key))) })), _jsx("div", { className: "schema-section-footer", children: addOpen ? (_jsx(AddFieldForm, { existingNames: new Set(allSections.flatMap((s) => s.fields.map((f) => f.name))), onCancel: () => setAddOpen(false), onSubmit: (f) => {
                        onAddField(f);
                        setAddOpen(false);
                    } })) : (_jsx("button", { type: "button", onClick: () => setAddOpen(true), children: "+ Add custom field" })) })] }));
}
function AddFieldForm({ existingNames, onCancel, onSubmit, }) {
    const [label, setLabel] = useState("");
    const [name, setName] = useState("");
    const [nameTouched, setNameTouched] = useState(false);
    const [type, setType] = useState("text");
    const [required, setRequired] = useState(false);
    const [error, setError] = useState(null);
    const suggested = suggestFieldName(label);
    const effectiveName = nameTouched ? name : suggested;
    const validate = () => {
        if (!label.trim())
            return "Label is required.";
        if (!effectiveName)
            return "Internal name is required.";
        if (!/^[a-z][a-z0-9_]{0,49}$/.test(effectiveName))
            return "Internal name must start with a letter and contain only lowercase letters, digits, and underscores.";
        if (existingNames.has(effectiveName))
            return `'${effectiveName}' is already used.`;
        return null;
    };
    const handleSubmit = (e) => {
        e.preventDefault();
        const err = validate();
        if (err) {
            setError(err);
            return;
        }
        const field = {
            _key: uniqueKey("field"),
            _isNew: true,
            name: effectiveName,
            label: label.trim(),
            type,
            required: type === "boolean" ? false : required,
            source: "custom",
            options: type === "select"
                ? [
                    { value: "option_1", label: "Option 1" },
                    { value: "option_2", label: "Option 2" },
                ]
                : undefined,
        };
        onSubmit(field);
    };
    return (_jsxs("form", { className: "add-field-form", onSubmit: handleSubmit, children: [_jsxs("div", { className: "add-field-grid", children: [_jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", style: { fontSize: 11 }, children: "Question (what the requester sees)" }), _jsx("input", { type: "text", value: label, onChange: (e) => setLabel(e.target.value), placeholder: "e.g. Cost center", autoFocus: true })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", style: { fontSize: 11 }, children: "Internal name (locked after save)" }), _jsx("input", { type: "text", value: effectiveName, onChange: (e) => {
                                    setNameTouched(true);
                                    setName(e.target.value);
                                }, placeholder: "cost_center", style: {
                                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                                } })] }), _jsxs("label", { className: "field", style: { margin: 0 }, children: [_jsx("span", { className: "label", style: { fontSize: 11 }, children: "Type" }), _jsxs("select", { value: type, onChange: (e) => setType(e.target.value), children: [_jsx("option", { value: "text", children: "Text \u2014 single line" }), _jsx("option", { value: "textarea", children: "Long text \u2014 paragraph" }), _jsx("option", { value: "select", children: "Dropdown \u2014 choose one" }), _jsx("option", { value: "boolean", children: "Yes / no \u2014 checkbox" })] })] }), _jsxs("label", { className: "inline-toggle", style: { alignSelf: "end", paddingBottom: 8 }, children: [_jsx("input", { type: "checkbox", checked: type === "boolean" ? false : required, disabled: type === "boolean", onChange: (e) => setRequired(e.target.checked) }), _jsx("span", { children: "Required" })] })] }), error && _jsx("div", { className: "error", style: { marginTop: 8 }, children: error }), _jsxs("div", { className: "form-actions", style: { marginTop: 8 }, children: [_jsx("button", { type: "submit", className: "primary", children: "Add field" }), _jsx("button", { type: "button", onClick: onCancel, children: "Cancel" })] })] }));
}
