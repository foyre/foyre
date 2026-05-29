import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { createPipeline, updatePipeline, validatePipeline, } from "../../api/validationPipelines";
const STARTER_YAML = `apiVersion: foyre.ai/v1alpha1
kind: ValidationPipeline
metadata:
  name: my-pipeline
  displayName: My Pipeline
  description: Describe what this pipeline validates.
spec:
  failurePolicy: warn
  steps:
    - name: workload-inventory
      type: builtin.workload_inventory
      required: true
      failurePolicy: warn
    - name: kubernetes-security
      type: builtin.kubernetes_security
      required: true
      failurePolicy: block
      dependsOn:
        - workload-inventory
`;
export function PipelineEditor({ pipeline, onSaved, onCancel }) {
    const editing = Boolean(pipeline);
    const [yaml, setYaml] = useState(pipeline?.definition_yaml ?? STARTER_YAML);
    const [isDefault, setIsDefault] = useState(pipeline?.is_default ?? false);
    const [validateMsg, setValidateMsg] = useState(null);
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    const onValidate = async () => {
        setError(null);
        setValidateMsg(null);
        setBusy(true);
        try {
            const res = await validatePipeline(yaml);
            if (res.valid) {
                const steps = res.normalized?.steps?.length ?? 0;
                setValidateMsg({
                    ok: true,
                    text: `Valid — ${steps} step(s).`,
                });
            }
            else {
                setValidateMsg({ ok: false, text: res.error ?? "Invalid pipeline." });
            }
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    const onSave = async () => {
        setError(null);
        setBusy(true);
        try {
            if (editing && pipeline) {
                await updatePipeline(pipeline.id, { definition_yaml: yaml });
            }
            else {
                await createPipeline({ definition_yaml: yaml, is_default: isDefault });
            }
            onSaved();
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs("div", { className: "card", style: { marginBottom: 16 }, children: [_jsx("h4", { style: { marginTop: 0, marginBottom: 4 }, children: editing ? `Edit pipeline: ${pipeline?.display_name}` : "New pipeline" }), _jsxs("p", { className: "muted", style: { marginTop: 0, marginBottom: 12, fontSize: 13 }, children: ["Pipelines are defined in YAML. Built-in step types:", " ", _jsx("code", { children: "builtin.workload_inventory" }), ",", " ", _jsx("code", { children: "builtin.kubernetes_security" }), ", ", _jsx("code", { children: "builtin.image_scan" }), ", and ", _jsx("code", { children: "custom.kubernetes_job" }), ". Validate before saving."] }), error && _jsx("div", { className: "error", children: error }), _jsx("textarea", { value: yaml, onChange: (e) => {
                    setYaml(e.target.value);
                    setValidateMsg(null);
                }, rows: 20, spellCheck: false, style: {
                    width: "100%",
                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                    fontSize: 13,
                } }), validateMsg && (_jsxs("div", { className: validateMsg.ok ? "muted" : "error", style: { marginTop: 8, whiteSpace: "pre-wrap" }, children: [validateMsg.ok ? "✓ " : "", validateMsg.text] })), !editing && (_jsxs("label", { className: "inline-toggle", style: { marginTop: 12 }, children: [_jsx("input", { type: "checkbox", checked: isDefault, onChange: (e) => setIsDefault(e.target.checked) }), _jsx("span", { children: "Make this the default pipeline" })] })), _jsxs("div", { className: "form-actions", style: { marginTop: 12 }, children: [_jsx("button", { type: "button", onClick: onValidate, disabled: busy, children: "Validate" }), _jsx("button", { type: "button", className: "primary", onClick: onSave, disabled: busy, children: busy ? "Saving…" : editing ? "Save changes" : "Create pipeline" }), _jsx("button", { type: "button", onClick: onCancel, disabled: busy, children: "Cancel" })] })] }));
}
