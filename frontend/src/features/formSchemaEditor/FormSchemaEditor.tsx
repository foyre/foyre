import { useEffect, useMemo, useState } from "react";
import {
  getAdminFormSchema,
  resetAdminFormSchema,
  updateAdminFormSchema,
} from "../../api/formSchema";
import { apiErrorMessage } from "../../api/errors";
import { FormPreview } from "./FormPreview";
import { SchemaSectionCard } from "./SchemaSectionCard";
import {
  type EditorField,
  type EditorSection,
  generateSectionId,
  toApi,
  toEditor,
  uniqueKey,
} from "./types";

export function FormSchemaEditor() {
  const [sections, setSections] = useState<EditorSection[] | null>(null);
  const [meta, setMeta] = useState<{
    isCustomized: boolean;
    updatedAt: string | null;
    updatedBy: string | null;
  }>({ isCustomized: false, updatedAt: null, updatedBy: null });
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [busy, setBusy] = useState<"save" | "reset" | null>(null);
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
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };

  useEffect(() => {
    reload();
  }, []);

  const update = (mutator: (prev: EditorSection[]) => EditorSection[]) => {
    setSections((prev) => (prev === null ? prev : mutator(prev)));
    setDirty(true);
    setFlash(null);
  };

  const patchSection = (key: string, patch: Partial<EditorSection>) =>
    update((prev) => prev.map((s) => (s._key === key ? { ...s, ...patch } : s)));

  const moveSection = (key: string, delta: number) =>
    update((prev) => {
      const idx = prev.findIndex((s) => s._key === key);
      const newIdx = idx + delta;
      if (idx < 0 || newIdx < 0 || newIdx >= prev.length) return prev;
      const next = [...prev];
      const [moved] = next.splice(idx, 1);
      next.splice(newIdx, 0, moved);
      return next;
    });

  const deleteSection = (key: string) =>
    update((prev) => prev.filter((s) => s._key !== key));

  const addSection = () =>
    update((prev) => [
      ...prev,
      {
        _key: uniqueKey("section"),
        id: generateSectionId(`Section ${prev.length + 1}`),
        title: `Section ${prev.length + 1}`,
        fields: [],
      },
    ]);

  const patchField = (sectionKey: string, fieldKey: string, patch: Partial<EditorField>) =>
    update((prev) =>
      prev.map((s) =>
        s._key !== sectionKey
          ? s
          : {
              ...s,
              fields: s.fields.map((f) => (f._key === fieldKey ? { ...f, ...patch } : f)),
            },
      ),
    );

  const deleteField = (sectionKey: string, fieldKey: string) => {
    const section = sections?.find((s) => s._key === sectionKey);
    const field = section?.fields.find((f) => f._key === fieldKey);
    if (!field) return;
    if (
      !window.confirm(
        `Remove the custom field "${field.label}"?\n\n` +
          "Existing requests that already have a value for this field will keep that value as orphan data, but it won't be displayed anywhere.",
      )
    )
      return;
    update((prev) =>
      prev.map((s) =>
        s._key !== sectionKey ? s : { ...s, fields: s.fields.filter((f) => f._key !== fieldKey) },
      ),
    );
  };

  const moveField = (sectionKey: string, fieldKey: string, delta: number) =>
    update((prev) =>
      prev.map((s) => {
        if (s._key !== sectionKey) return s;
        const idx = s.fields.findIndex((f) => f._key === fieldKey);
        const newIdx = idx + delta;
        if (idx < 0 || newIdx < 0 || newIdx >= s.fields.length) return s;
        const fields = [...s.fields];
        const [moved] = fields.splice(idx, 1);
        fields.splice(newIdx, 0, moved);
        return { ...s, fields };
      }),
    );

  const moveFieldToSection = (
    fromSectionKey: string,
    fieldKey: string,
    targetSectionId: string,
  ) =>
    update((prev) => {
      const fromSection = prev.find((s) => s._key === fromSectionKey);
      const field = fromSection?.fields.find((f) => f._key === fieldKey);
      if (!field) return prev;
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

  const addField = (sectionKey: string, field: EditorField) =>
    update((prev) =>
      prev.map((s) => (s._key !== sectionKey ? s : { ...s, fields: [...s.fields, field] })),
    );

  const handleSave = async () => {
    if (!sections) return;
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
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const handleReset = async () => {
    if (
      !window.confirm(
        "Restore the default form?\n\n" +
          "All custom fields and label changes will be removed. Existing request answers stay in the database but custom-field values won't be displayed.",
      )
    )
      return;
    setBusy("reset");
    setError(null);
    setFlash(null);
    try {
      await resetAdminFormSchema();
      await reload();
      setFlash("Restored built-in default form.");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const validationErrors = useMemo(() => {
    if (!sections) return [];
    const errs: string[] = [];
    const seenNames = new Set<string>();
    const seenSectionIds = new Set<string>();
    for (const s of sections) {
      if (!s.title.trim()) errs.push(`Section "${s.id}" needs a title.`);
      if (seenSectionIds.has(s.id))
        errs.push(`Two sections have the same id "${s.id}".`);
      seenSectionIds.add(s.id);
      for (const f of s.fields) {
        if (!f.label.trim()) errs.push(`Field "${f.name}" needs a label.`);
        if (!f.name.trim()) errs.push("All custom fields need an internal name.");
        if (seenNames.has(f.name))
          errs.push(`Field name "${f.name}" appears more than once.`);
        seenNames.add(f.name);
        if (f.source !== "core" && !/^[a-z][a-z0-9_]{0,49}$/.test(f.name)) {
          errs.push(
            `Field "${f.name}" has an invalid internal name (use lowercase, digits, underscores).`,
          );
        }
        if (f.type === "select" && f.source !== "core") {
          if (!f.options || f.options.length === 0)
            errs.push(`Dropdown "${f.name}" needs at least one option.`);
          const optVals = new Set<string>();
          for (const o of f.options ?? []) {
            if (!o.value.trim()) errs.push(`Dropdown "${f.name}" has an empty option value.`);
            if (!o.label.trim()) errs.push(`Dropdown "${f.name}" has an empty option label.`);
            if (optVals.has(o.value))
              errs.push(`Dropdown "${f.name}" has duplicate option value "${o.value}".`);
            optVals.add(o.value);
          }
        }
      }
    }
    return errs;
  }, [sections]);

  if (sections === null) return <p className="muted">Loading form schema…</p>;

  return (
    <div>
      <div className="schema-editor-header">
        <div>
          <p className="muted" style={{ margin: 0, maxWidth: 720 }}>
            Customize the intake form requesters fill in. Built-in fields can
            be relabeled and moved around but not removed, because the risk
            engine depends on them. Add your own custom fields to ask
            organization-specific questions.
          </p>
          {meta.isCustomized ? (
            <p className="muted" style={{ marginTop: 6, fontSize: 12 }}>
              Custom schema active.
              {meta.updatedBy && <> Last edited by <strong>{meta.updatedBy}</strong></>}
              {meta.updatedAt && (
                <> · {new Date(meta.updatedAt).toLocaleString()}</>
              )}
            </p>
          ) : (
            <p className="muted" style={{ marginTop: 6, fontSize: 12 }}>
              You're using the built-in default schema. Any change saves a
              customization.
            </p>
          )}
        </div>
        <div className="schema-editor-actions">
          <label className="inline-toggle" style={{ marginRight: 8 }}>
            <input
              type="checkbox"
              checked={showPreview}
              onChange={(e) => setShowPreview(e.target.checked)}
            />
            <span>Live preview</span>
          </label>
          <button
            type="button"
            onClick={handleReset}
            disabled={busy !== null || !meta.isCustomized}
            title={
              meta.isCustomized
                ? "Discard your customization and restore Foyre's built-in form."
                : "Already on the built-in default."
            }
          >
            {busy === "reset" ? "Resetting…" : "Reset to default"}
          </button>
          <button
            type="button"
            className="primary"
            onClick={handleSave}
            disabled={busy !== null || !dirty || validationErrors.length > 0}
            title={
              !dirty
                ? "No unsaved changes."
                : validationErrors.length > 0
                  ? "Fix the validation issues below first."
                  : "Save the customized form schema."
            }
          >
            {busy === "save" ? "Saving…" : dirty ? "Save changes" : "Saved"}
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {flash && (
        <div className="muted" style={{ marginBottom: 12 }}>
          {flash}
        </div>
      )}
      {validationErrors.length > 0 && (
        <div className="error">
          <strong>Fix these before saving:</strong>
          <ul style={{ margin: "6px 0 0 18px" }}>
            {validationErrors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      <div className={showPreview ? "schema-editor-split" : ""}>
        <div className="schema-editor-main">
          {sections.map((s, i) => (
            <SchemaSectionCard
              key={s._key}
              section={s}
              allSections={sections}
              index={i}
              total={sections.length}
              onPatch={(patch) => patchSection(s._key, patch)}
              onMoveUp={() => moveSection(s._key, -1)}
              onMoveDown={() => moveSection(s._key, 1)}
              onDelete={() => deleteSection(s._key)}
              onPatchField={(fk, p) => patchField(s._key, fk, p)}
              onDeleteField={(fk) => deleteField(s._key, fk)}
              onMoveFieldUp={(fk) => moveField(s._key, fk, -1)}
              onMoveFieldDown={(fk) => moveField(s._key, fk, 1)}
              onMoveFieldToSection={(fk, sid) => moveFieldToSection(s._key, fk, sid)}
              onAddField={(f) => addField(s._key, f)}
            />
          ))}
          <div style={{ marginTop: 16 }}>
            <button type="button" onClick={addSection}>
              + Add section
            </button>
          </div>
        </div>

        {showPreview && (
          <aside className="schema-editor-preview">
            <div className="schema-preview-header">
              <h4 style={{ margin: 0 }}>Live preview</h4>
              <span className="muted" style={{ fontSize: 12 }}>
                What requesters will see
              </span>
            </div>
            <div className="schema-preview-body">
              <FormPreview sections={sections} />
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
