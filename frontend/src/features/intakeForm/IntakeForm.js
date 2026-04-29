import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../../api/client";
import { apiErrorMessage } from "../../api/errors";
import { getFormSchema } from "../../api/meta";
import { FormField } from "../../components/FormField";
function isVisible(field, values) {
    if (!field.visible_if)
        return true;
    return Object.entries(field.visible_if).every(([k, v]) => values[k] === v);
}
function isEmpty(v) {
    if (v === undefined || v === null)
        return true;
    if (typeof v === "string" && v.trim() === "")
        return true;
    return false;
}
/** Remove values for fields whose `visible_if` no longer matches. */
function pruneHidden(sections, values) {
    const visibleNames = new Set();
    for (const s of sections)
        for (const f of s.fields)
            if (isVisible(f, values))
                visibleNames.add(f.name);
    const out = {};
    for (const [k, v] of Object.entries(values))
        if (visibleNames.has(k))
            out[k] = v;
    return out;
}
function validateRequired(sections, values) {
    const errs = {};
    for (const s of sections) {
        for (const f of s.fields) {
            if (!f.required)
                continue;
            if (!isVisible(f, values))
                continue;
            if (isEmpty(values[f.name]))
                errs[f.name] = "Required";
        }
    }
    return errs;
}
function fieldErrorsFromApiError(err) {
    if (!(err instanceof ApiError) || err.status !== 422)
        return {};
    const detail = err.detail;
    const result = {};
    for (const e of detail?.errors ?? []) {
        const name = typeof e.loc[0] === "string" ? e.loc[0] : undefined;
        if (!name)
            continue;
        result[name] = e.type === "missing" ? "Required" : e.msg || "Invalid";
    }
    return result;
}
export function IntakeForm({ initialValues, onSaveDraft, onSubmit }) {
    const [schema, setSchema] = useState(null);
    const [values, setValues] = useState(initialValues ?? {});
    const [errors, setErrors] = useState({});
    const [flash, setFlash] = useState(null);
    const [formError, setFormError] = useState(null);
    const [busy, setBusy] = useState(null);
    useEffect(() => {
        getFormSchema().then(setSchema);
    }, []);
    const sections = useMemo(() => schema?.sections ?? [], [schema]);
    if (!schema)
        return _jsx("p", { className: "muted", children: "Loading form\u2026" });
    const setField = (name, v) => setValues((prev) => {
        const next = { ...prev, [name]: v };
        return pruneHidden(sections, next);
    });
    const onFieldChange = (name, v) => {
        setField(name, v);
        if (errors[name]) {
            setErrors((prev) => {
                const { [name]: _ignored, ...rest } = prev;
                return rest;
            });
        }
        setFormError(null);
    };
    const handleSaveDraft = async () => {
        setBusy("draft");
        setFormError(null);
        setFlash(null);
        try {
            await onSaveDraft(values);
            setFlash("Draft saved.");
        }
        catch (err) {
            setFormError(apiErrorMessage(err));
        }
        finally {
            setBusy(null);
        }
    };
    const handleSubmit = async () => {
        setFormError(null);
        setFlash(null);
        const missing = validateRequired(sections, values);
        if (Object.keys(missing).length) {
            setErrors(missing);
            setFormError("Please fill in the required fields.");
            return;
        }
        setBusy("submit");
        try {
            await onSubmit(values);
        }
        catch (err) {
            const fieldErrs = fieldErrorsFromApiError(err);
            if (Object.keys(fieldErrs).length)
                setErrors(fieldErrs);
            setFormError(apiErrorMessage(err));
        }
        finally {
            setBusy(null);
        }
    };
    return (_jsxs("form", { onSubmit: (e) => e.preventDefault(), children: [formError && _jsx("div", { className: "error", children: formError }), sections.map((section) => (_jsxs("fieldset", { className: "form-section", children: [_jsx("legend", { children: section.title }), section.fields
                        .filter((f) => isVisible(f, values))
                        .map((f) => (_jsx(FormField, { field: f, value: values[f.name], error: errors[f.name], onChange: (v) => onFieldChange(f.name, v) }, f.name)))] }, section.id))), _jsxs("div", { className: "form-actions", children: [_jsx("button", { type: "button", onClick: handleSaveDraft, disabled: busy !== null, children: busy === "draft" ? "Saving…" : "Save draft" }), _jsx("button", { type: "button", className: "primary", onClick: handleSubmit, disabled: busy !== null, children: busy === "submit" ? "Submitting…" : "Submit" }), flash && _jsx("span", { className: "flash", children: flash })] })] }));
}
