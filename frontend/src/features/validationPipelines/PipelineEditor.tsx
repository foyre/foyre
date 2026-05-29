import { useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import {
  createPipeline,
  updatePipeline,
  validatePipeline,
} from "../../api/validationPipelines";
import type { Pipeline } from "../../types/domain";

interface Props {
  /** Editing an existing pipeline, or undefined to create a new one. */
  pipeline?: Pipeline;
  onSaved: () => void;
  onCancel: () => void;
}

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

export function PipelineEditor({ pipeline, onSaved, onCancel }: Props) {
  const editing = Boolean(pipeline);
  const [yaml, setYaml] = useState(pipeline?.definition_yaml ?? STARTER_YAML);
  const [isDefault, setIsDefault] = useState(pipeline?.is_default ?? false);
  const [validateMsg, setValidateMsg] = useState<{
    ok: boolean;
    text: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onValidate = async () => {
    setError(null);
    setValidateMsg(null);
    setBusy(true);
    try {
      const res = await validatePipeline(yaml);
      if (res.valid) {
        const steps =
          (res.normalized?.steps as unknown[] | undefined)?.length ?? 0;
        setValidateMsg({
          ok: true,
          text: `Valid — ${steps} step(s).`,
        });
      } else {
        setValidateMsg({ ok: false, text: res.error ?? "Invalid pipeline." });
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const onSave = async () => {
    setError(null);
    setBusy(true);
    try {
      if (editing && pipeline) {
        await updatePipeline(pipeline.id, { definition_yaml: yaml });
      } else {
        await createPipeline({ definition_yaml: yaml, is_default: isDefault });
      }
      onSaved();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <h4 style={{ marginTop: 0, marginBottom: 4 }}>
        {editing ? `Edit pipeline: ${pipeline?.display_name}` : "New pipeline"}
      </h4>
      <p className="muted" style={{ marginTop: 0, marginBottom: 12, fontSize: 13 }}>
        Pipelines are defined in YAML. Built-in step types:{" "}
        <code>builtin.workload_inventory</code>,{" "}
        <code>builtin.kubernetes_security</code>, <code>builtin.image_scan</code>,
        and <code>custom.kubernetes_job</code>. Validate before saving.
      </p>

      {error && <div className="error">{error}</div>}

      <textarea
        value={yaml}
        onChange={(e) => {
          setYaml(e.target.value);
          setValidateMsg(null);
        }}
        rows={20}
        spellCheck={false}
        style={{
          width: "100%",
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
          fontSize: 13,
        }}
      />

      {validateMsg && (
        <div
          className={validateMsg.ok ? "muted" : "error"}
          style={{ marginTop: 8, whiteSpace: "pre-wrap" }}
        >
          {validateMsg.ok ? "✓ " : ""}
          {validateMsg.text}
        </div>
      )}

      {!editing && (
        <label className="inline-toggle" style={{ marginTop: 12 }}>
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
          />
          <span>Make this the default pipeline</span>
        </label>
      )}

      <div className="form-actions" style={{ marginTop: 12 }}>
        <button type="button" onClick={onValidate} disabled={busy}>
          Validate
        </button>
        <button
          type="button"
          className="primary"
          onClick={onSave}
          disabled={busy}
        >
          {busy ? "Saving…" : editing ? "Save changes" : "Create pipeline"}
        </button>
        <button type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </div>
  );
}
