import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
const TYPE_LABEL = {
    text: "Text",
    textarea: "Long text",
    select: "Dropdown",
    boolean: "Yes / no",
};
export function FieldRow({ field, sections, currentSectionId, canMoveUp, canMoveDown, onPatch, onMoveUp, onMoveDown, onDelete, onMoveToSection, }) {
    const isCore = field.source === "core";
    const isNew = !!field._isNew;
    const isSelect = field.type === "select";
    const [optionsOpen, setOptionsOpen] = useState(false);
    // Backend allows admins to relabel core fields but NOT change anything
    // else; we mirror that here.
    return (_jsxs("div", { className: "schema-field", children: [_jsxs("div", { className: "schema-field-main", children: [_jsxs("div", { className: "schema-field-reorder", children: [_jsx("button", { type: "button", className: "icon-btn", onClick: onMoveUp, disabled: !canMoveUp, title: "Move up", "aria-label": "Move field up", children: "\u2191" }), _jsx("button", { type: "button", className: "icon-btn", onClick: onMoveDown, disabled: !canMoveDown, title: "Move down", "aria-label": "Move field down", children: "\u2193" })] }), _jsxs("div", { className: "schema-field-body", children: [_jsxs("div", { className: "schema-field-headline", children: [_jsx("span", { className: `field-source-pill ${isCore ? "is-core" : "is-custom"}`, children: isCore ? "Built-in" : "Custom" }), _jsx("span", { className: "field-type-pill", children: TYPE_LABEL[field.type] }), _jsx("code", { className: "field-name-mono", children: field.name }), field.required && (_jsx("span", { className: "field-req-pill", title: "Required", children: "Required" }))] }), _jsxs("label", { className: "field", style: { marginBottom: 0, marginTop: 6 }, children: [_jsx("span", { className: "label", style: { fontSize: 11 }, children: "Question shown to requester" }), _jsx("input", { type: "text", value: field.label, onChange: (e) => onPatch({ label: e.target.value }), placeholder: "Field label" })] }), isNew && !isCore && (_jsxs("div", { className: "schema-field-extras", children: [_jsxs("label", { className: "field", style: { marginBottom: 0 }, children: [_jsx("span", { className: "label", style: { fontSize: 11 }, children: "Internal name" }), _jsx("input", { type: "text", value: field.name, onChange: (e) => onPatch({ name: e.target.value }), placeholder: "cost_center", style: {
                                                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                                                } }), _jsx("span", { className: "muted", style: { fontSize: 11 }, children: "Lowercase, digits, underscores. Locked after first save." })] }), _jsxs("label", { className: "field", style: { marginBottom: 0 }, children: [_jsx("span", { className: "label", style: { fontSize: 11 }, children: "Type" }), _jsxs("select", { value: field.type, onChange: (e) => {
                                                    const newType = e.target.value;
                                                    const patch = { type: newType };
                                                    if (newType === "select" && !field.options) {
                                                        patch.options = [{ value: "option_1", label: "Option 1" }];
                                                    }
                                                    else if (newType !== "select") {
                                                        patch.options = undefined;
                                                    }
                                                    onPatch(patch);
                                                }, children: [_jsx("option", { value: "text", children: "Text \u2014 single line" }), _jsx("option", { value: "textarea", children: "Long text \u2014 paragraph" }), _jsx("option", { value: "select", children: "Dropdown \u2014 choose one" }), _jsx("option", { value: "boolean", children: "Yes / no \u2014 checkbox" })] })] })] }))] })] }), _jsxs("div", { className: "schema-field-controls", children: [!isCore && (_jsxs("label", { className: "inline-toggle", title: field.type === "boolean"
                            ? "Booleans default to false; 'required' has no effect."
                            : "Force the requester to fill this in before submitting.", children: [_jsx("input", { type: "checkbox", checked: !!field.required, onChange: (e) => onPatch({ required: e.target.checked }), disabled: field.type === "boolean" }), _jsx("span", { children: "Required" })] })), sections.length > 1 && (_jsx("select", { value: currentSectionId, onChange: (e) => onMoveToSection(e.target.value), title: "Move this field into a different section", className: "schema-section-select", children: sections.map((s) => (_jsxs("option", { value: s.id, children: ["Section: ", s.title || "(untitled)"] }, s._key))) })), isSelect && (_jsx("button", { type: "button", onClick: () => setOptionsOpen((v) => !v), disabled: isCore, title: isCore
                            ? "Built-in select options are tied to backend logic and can't be changed."
                            : "Edit dropdown options", children: optionsOpen ? "Close options" : `Options (${field.options?.length ?? 0})` })), !isCore && (_jsx("button", { type: "button", onClick: onDelete, className: "danger-btn", title: "Remove this custom field. Existing answers will become orphan data.", children: "Remove" }))] }), isSelect && optionsOpen && !isCore && (_jsx(OptionsEditor, { options: field.options ?? [], onChange: (options) => onPatch({ options }) }))] }));
}
function OptionsEditor({ options, onChange, }) {
    return (_jsxs("div", { className: "schema-options-editor", children: [_jsxs("div", { className: "schema-options-header", children: [_jsx("span", { className: "muted", style: { fontSize: 12 }, children: "Internal value" }), _jsx("span", { className: "muted", style: { fontSize: 12 }, children: "Label shown to requester" }), _jsx("span", {})] }), options.map((opt, i) => (_jsxs("div", { className: "schema-option-row", children: [_jsx("input", { type: "text", value: opt.value, onChange: (e) => {
                            const next = [...options];
                            next[i] = { ...opt, value: e.target.value };
                            onChange(next);
                        }, placeholder: "value", style: {
                            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                        } }), _jsx("input", { type: "text", value: opt.label, onChange: (e) => {
                            const next = [...options];
                            next[i] = { ...opt, label: e.target.value };
                            onChange(next);
                        }, placeholder: "Display label" }), _jsx("button", { type: "button", onClick: () => onChange(options.filter((_, j) => j !== i)), disabled: options.length <= 1, title: options.length <= 1
                            ? "A dropdown needs at least one option."
                            : "Remove this option", children: "\u2715" })] }, i))), _jsx("button", { type: "button", onClick: () => onChange([
                    ...options,
                    { value: `option_${options.length + 1}`, label: `Option ${options.length + 1}` },
                ]), children: "Add option" })] }));
}
