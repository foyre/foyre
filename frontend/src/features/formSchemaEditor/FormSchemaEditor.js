import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { getAdminFormSchema, resetAdminFormSchema, updateAdminFormSchema, } from "../../api/formSchema";
import { apiErrorMessage } from "../../api/errors";
import { FormPreview } from "./FormPreview";
import { SchemaSectionCard } from "./SchemaSectionCard";
import { generateSectionId, toApi, toEditor, uniqueKey, } from "./types";
export function FormSchemaEditor() {
    const [sections, setSections] = useState(null);
    const [meta, setMeta] = useState({ isCustomized: false, updatedAt: null, updatedBy: null });
    const [error, setError] = useState(null);
    const [flash, setFlash] = useState(null);
    const [busy, setBusy] = useState(null);
    const [dirty, setDirty] = useState(false);
    const [showPreview, setShowPreview] = useState(true);
    const reload = async () => {
        try {
            const bundle = await getAdminFormSchema();
            setSections(toEditor(bundle.current.sections));
            setMeta({
                isCustomized: bundle.current.is_customized,
                updatedAt: bundle.current.updated_at,
                updatedBy: bundle.current.updated_by_username,
            });
            setDirty(false);
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
    };
    useEffect(() => {
        reload();
    }, []);
    const update = (mutator) => {
        setSections((prev) => (prev === null ? prev : mutator(prev)));
        setDirty(true);
        setFlash(null);
    };
    const patchSection = (key, patch) => update((prev) => prev.map((s) => (s._key === key ? { ...s, ...patch } : s)));
    const moveSection = (key, delta) => update((prev) => {
        const idx = prev.findIndex((s) => s._key === key);
        const newIdx = idx + delta;
        if (idx < 0 || newIdx < 0 || newIdx >= prev.length)
            return prev;
        const next = [...prev];
        const [moved] = next.splice(idx, 1);
        next.splice(newIdx, 0, moved);
        return next;
    });
    const deleteSection = (key) => update((prev) => prev.filter((s) => s._key !== key));
    const addSection = () => update((prev) => [
        ...prev,
        {
            _key: uniqueKey("section"),
            id: generateSectionId(`Section ${prev.length + 1}`),
            title: `Section ${prev.length + 1}`,
            fields: [],
        },
    ]);
    const patchField = (sectionKey, fieldKey, patch) => update((prev) => prev.map((s) => s._key !== sectionKey
        ? s
        : {
            ...s,
            fields: s.fields.map((f) => (f._key === fieldKey ? { ...f, ...patch } : f)),
        }));
    const deleteField = (sectionKey, fieldKey) => {
        const section = sections?.find((s) => s._key === sectionKey);
        const field = section?.fields.find((f) => f._key === fieldKey);
        if (!field)
            return;
        if (!window.confirm(`Remove the custom field "${field.label}"?\n\n` +
            "Existing requests that already have a value for this field will keep that value as orphan data, but it won't be displayed anywhere."))
            return;
        update((prev) => prev.map((s) => s._key !== sectionKey ? s : { ...s, fields: s.fields.filter((f) => f._key !== fieldKey) }));
    };
    const moveField = (sectionKey, fieldKey, delta) => update((prev) => prev.map((s) => {
        if (s._key !== sectionKey)
            return s;
        const idx = s.fields.findIndex((f) => f._key === fieldKey);
        const newIdx = idx + delta;
        if (idx < 0 || newIdx < 0 || newIdx >= s.fields.length)
            return s;
        const fields = [...s.fields];
        const [moved] = fields.splice(idx, 1);
        fields.splice(newIdx, 0, moved);
        return { ...s, fields };
    }));
    const moveFieldToSection = (fromSectionKey, fieldKey, targetSectionId) => update((prev) => {
        const fromSection = prev.find((s) => s._key === fromSectionKey);
        const field = fromSection?.fields.find((f) => f._key === fieldKey);
        if (!field)
            return prev;
        return prev.map((s) => {
            if (s._key === fromSectionKey) {
                return { ...s, fields: s.fields.filter((f) => f._key !== fieldKey) };
            }
            if (s.id === targetSectionId) {
                return { ...s, fields: [...s.fields, field] };
            }
            return s;
        });
    });
    const addField = (sectionKey, field) => update((prev) => prev.map((s) => (s._key !== sectionKey ? s : { ...s, fields: [...s.fields, field] })));
    const handleSave = async () => {
        if (!sections)
            return;
        setBusy("save");
        setError(null);
        setFlash(null);
        try {
            const bundle = await updateAdminFormSchema(toApi(sections));
            setSections(toEditor(bundle.current.sections));
            setMeta({
                isCustomized: bundle.current.is_customized,
                updatedAt: bundle.current.updated_at,
                updatedBy: bundle.current.updated_by_username,
            });
            setDirty(false);
            setFlash("Form schema saved.");
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(null);
        }
    };
    const handleReset = async () => {
        if (!window.confirm("Restore the default form?\n\n" +
            "All custom fields and label changes will be removed. Existing request answers stay in the database but custom-field values won't be displayed."))
            return;
        setBusy("reset");
        setError(null);
        setFlash(null);
        try {
            await resetAdminFormSchema();
            await reload();
            setFlash("Restored built-in default form.");
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(null);
        }
    };
    const validationErrors = useMemo(() => {
        if (!sections)
            return [];
        const errs = [];
        const seenNames = new Set();
        const seenSectionIds = new Set();
        for (const s of sections) {
            if (!s.title.trim())
                errs.push(`Section "${s.id}" needs a title.`);
            if (seenSectionIds.has(s.id))
                errs.push(`Two sections have the same id "${s.id}".`);
            seenSectionIds.add(s.id);
            for (const f of s.fields) {
                if (!f.label.trim())
                    errs.push(`Field "${f.name}" needs a label.`);
                if (!f.name.trim())
                    errs.push("All custom fields need an internal name.");
                if (seenNames.has(f.name))
                    errs.push(`Field name "${f.name}" appears more than once.`);
                seenNames.add(f.name);
                if (f.source !== "core" && !/^[a-z][a-z0-9_]{0,49}$/.test(f.name)) {
                    errs.push(`Field "${f.name}" has an invalid internal name (use lowercase, digits, underscores).`);
                }
                if (f.type === "select" && f.source !== "core") {
                    if (!f.options || f.options.length === 0)
                        errs.push(`Dropdown "${f.name}" needs at least one option.`);
                    const optVals = new Set();
                    for (const o of f.options ?? []) {
                        if (!o.value.trim())
                            errs.push(`Dropdown "${f.name}" has an empty option value.`);
                        if (!o.label.trim())
                            errs.push(`Dropdown "${f.name}" has an empty option label.`);
                        if (optVals.has(o.value))
                            errs.push(`Dropdown "${f.name}" has duplicate option value "${o.value}".`);
                        optVals.add(o.value);
                    }
                }
            }
        }
        return errs;
    }, [sections]);
    if (sections === null)
        return _jsx("p", { className: "muted", children: "Loading form schema\u2026" });
    return (_jsxs("div", { children: [_jsxs("div", { className: "schema-editor-header", children: [_jsxs("div", { children: [_jsx("p", { className: "muted", style: { margin: 0, maxWidth: 720 }, children: "Customize the intake form requesters fill in. Built-in fields can be relabeled and moved around but not removed, because the risk engine depends on them. Add your own custom fields to ask organization-specific questions." }), meta.isCustomized ? (_jsxs("p", { className: "muted", style: { marginTop: 6, fontSize: 12 }, children: ["Custom schema active.", meta.updatedBy && _jsxs(_Fragment, { children: [" Last edited by ", _jsx("strong", { children: meta.updatedBy })] }), meta.updatedAt && (_jsxs(_Fragment, { children: [" \u00B7 ", new Date(meta.updatedAt).toLocaleString()] }))] })) : (_jsx("p", { className: "muted", style: { marginTop: 6, fontSize: 12 }, children: "You're using the built-in default schema. Any change saves a customization." }))] }), _jsxs("div", { className: "schema-editor-actions", children: [_jsxs("label", { className: "inline-toggle", style: { marginRight: 8 }, children: [_jsx("input", { type: "checkbox", checked: showPreview, onChange: (e) => setShowPreview(e.target.checked) }), _jsx("span", { children: "Live preview" })] }), _jsx("button", { type: "button", onClick: handleReset, disabled: busy !== null || !meta.isCustomized, title: meta.isCustomized
                                    ? "Discard your customization and restore Foyre's built-in form."
                                    : "Already on the built-in default.", children: busy === "reset" ? "Resetting…" : "Reset to default" }), _jsx("button", { type: "button", className: "primary", onClick: handleSave, disabled: busy !== null || !dirty || validationErrors.length > 0, title: !dirty
                                    ? "No unsaved changes."
                                    : validationErrors.length > 0
                                        ? "Fix the validation issues below first."
                                        : "Save the customized form schema.", children: busy === "save" ? "Saving…" : dirty ? "Save changes" : "Saved" })] })] }), error && _jsx("div", { className: "error", children: error }), flash && (_jsx("div", { className: "muted", style: { marginBottom: 12 }, children: flash })), validationErrors.length > 0 && (_jsxs("div", { className: "error", children: [_jsx("strong", { children: "Fix these before saving:" }), _jsx("ul", { style: { margin: "6px 0 0 18px" }, children: validationErrors.map((e, i) => (_jsx("li", { children: e }, i))) })] })), _jsxs("div", { className: showPreview ? "schema-editor-split" : "", children: [_jsxs("div", { className: "schema-editor-main", children: [sections.map((s, i) => (_jsx(SchemaSectionCard, { section: s, allSections: sections, index: i, total: sections.length, onPatch: (patch) => patchSection(s._key, patch), onMoveUp: () => moveSection(s._key, -1), onMoveDown: () => moveSection(s._key, 1), onDelete: () => deleteSection(s._key), onPatchField: (fk, p) => patchField(s._key, fk, p), onDeleteField: (fk) => deleteField(s._key, fk), onMoveFieldUp: (fk) => moveField(s._key, fk, -1), onMoveFieldDown: (fk) => moveField(s._key, fk, 1), onMoveFieldToSection: (fk, sid) => moveFieldToSection(s._key, fk, sid), onAddField: (f) => addField(s._key, f) }, s._key))), _jsx("div", { style: { marginTop: 16 }, children: _jsx("button", { type: "button", onClick: addSection, children: "+ Add section" }) })] }), showPreview && (_jsxs("aside", { className: "schema-editor-preview", children: [_jsxs("div", { className: "schema-preview-header", children: [_jsx("h4", { style: { margin: 0 }, children: "Live preview" }), _jsx("span", { className: "muted", style: { fontSize: 12 }, children: "What requesters will see" })] }), _jsx("div", { className: "schema-preview-body", children: _jsx(FormPreview, { sections: sections }) })] }))] })] }));
}
