import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../../api/client";
import { apiErrorMessage } from "../../api/errors";
import { getFormSchema } from "../../api/meta";
import { FormField } from "../../components/FormField";
import type {
  FormField as FieldDef,
  FormSchema,
  FormSection,
} from "../../types/domain";

type Values = Record<string, unknown>;
type Errors = Record<string, string>;

interface Props {
  initialValues?: Values;
  onSaveDraft: (values: Values) => Promise<void>;
  onSubmit: (values: Values) => Promise<void>;
}

function isVisible(field: FieldDef, values: Values): boolean {
  if (!field.visible_if) return true;
  return Object.entries(field.visible_if).every(([k, v]) => values[k] === v);
}

function isEmpty(v: unknown): boolean {
  if (v === undefined || v === null) return true;
  if (typeof v === "string" && v.trim() === "") return true;
  return false;
}

/** Remove values for fields whose `visible_if` no longer matches. */
function pruneHidden(sections: FormSection[], values: Values): Values {
  const visibleNames = new Set<string>();
  for (const s of sections)
    for (const f of s.fields) if (isVisible(f, values)) visibleNames.add(f.name);
  const out: Values = {};
  for (const [k, v] of Object.entries(values))
    if (visibleNames.has(k)) out[k] = v;
  return out;
}

function validateRequired(sections: FormSection[], values: Values): Errors {
  const errs: Errors = {};
  for (const s of sections) {
    for (const f of s.fields) {
      if (!f.required) continue;
      if (!isVisible(f, values)) continue;
      if (isEmpty(values[f.name])) errs[f.name] = "Required";
    }
  }
  return errs;
}

interface PydanticErr {
  loc: (string | number)[];
  msg: string;
  type: string;
}

function fieldErrorsFromApiError(err: unknown): Errors {
  if (!(err instanceof ApiError) || err.status !== 422) return {};
  const detail = err.detail as { errors?: PydanticErr[] } | undefined;
  const result: Errors = {};
  for (const e of detail?.errors ?? []) {
    const name = typeof e.loc[0] === "string" ? (e.loc[0] as string) : undefined;
    if (!name) continue;
    result[name] = e.type === "missing" ? "Required" : e.msg || "Invalid";
  }
  return result;
}

export function IntakeForm({ initialValues, onSaveDraft, onSubmit }: Props) {
  const [schema, setSchema] = useState<FormSchema | null>(null);
  const [values, setValues] = useState<Values>(initialValues ?? {});
  const [errors, setErrors] = useState<Errors>({});
  const [flash, setFlash] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"draft" | "submit" | null>(null);

  useEffect(() => {
    getFormSchema().then(setSchema);
  }, []);

  const sections = useMemo(() => schema?.sections ?? [], [schema]);

  if (!schema) return <p className="muted">Loading form…</p>;

  const setField = (name: string, v: unknown) =>
    setValues((prev) => {
      const next = { ...prev, [name]: v };
      return pruneHidden(sections, next);
    });

  const onFieldChange = (name: string, v: unknown) => {
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
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
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
    } catch (err) {
      const fieldErrs = fieldErrorsFromApiError(err);
      if (Object.keys(fieldErrs).length) setErrors(fieldErrs);
      setFormError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  return (
    <form onSubmit={(e) => e.preventDefault()}>
      {formError && <div className="error">{formError}</div>}

      {sections.map((section) => (
        <fieldset key={section.id} className="form-section">
          <legend>{section.title}</legend>
          {section.fields
            .filter((f) => isVisible(f, values))
            .map((f) => (
              <FormField
                key={f.name}
                field={f}
                value={values[f.name]}
                error={errors[f.name]}
                onChange={(v) => onFieldChange(f.name, v)}
              />
            ))}
        </fieldset>
      ))}

      <div className="form-actions">
        <button
          type="button"
          onClick={handleSaveDraft}
          disabled={busy !== null}
        >
          {busy === "draft" ? "Saving…" : "Save draft"}
        </button>
        <button
          type="button"
          className="primary"
          onClick={handleSubmit}
          disabled={busy !== null}
        >
          {busy === "submit" ? "Submitting…" : "Submit"}
        </button>
        {flash && <span className="flash">{flash}</span>}
      </div>
    </form>
  );
}
