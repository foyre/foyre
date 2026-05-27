import { useState } from "react";
import type { FormFieldType } from "../../types/domain";
import { FieldRow } from "./FieldRow";
import {
  type EditorField,
  type EditorSection,
  suggestFieldName,
  uniqueKey,
} from "./types";

interface Props {
  section: EditorSection;
  allSections: EditorSection[];
  index: number;
  total: number;
  onPatch: (patch: Partial<EditorSection>) => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onDelete: () => void;
  onPatchField: (fieldKey: string, patch: Partial<EditorField>) => void;
  onDeleteField: (fieldKey: string) => void;
  onMoveFieldUp: (fieldKey: string) => void;
  onMoveFieldDown: (fieldKey: string) => void;
  onMoveFieldToSection: (fieldKey: string, sectionId: string) => void;
  onAddField: (field: EditorField) => void;
}

export function SchemaSectionCard({
  section,
  allSections,
  index,
  total,
  onPatch,
  onMoveUp,
  onMoveDown,
  onDelete,
  onPatchField,
  onDeleteField,
  onMoveFieldUp,
  onMoveFieldDown,
  onMoveFieldToSection,
  onAddField,
}: Props) {
  const [addOpen, setAddOpen] = useState(false);
  const hasCoreFields = section.fields.some((f) => f.source === "core");
  const canDelete = section.fields.length === 0 || !hasCoreFields;

  return (
    <div className="schema-section-card">
      <div className="schema-section-header">
        <div className="schema-section-reorder">
          <button
            type="button"
            className="icon-btn"
            onClick={onMoveUp}
            disabled={index === 0}
            title="Move section up"
            aria-label="Move section up"
          >
            ↑
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={onMoveDown}
            disabled={index === total - 1}
            title="Move section down"
            aria-label="Move section down"
          >
            ↓
          </button>
        </div>
        <input
          className="schema-section-title-input"
          type="text"
          value={section.title}
          onChange={(e) => onPatch({ title: e.target.value })}
          placeholder="Section title"
        />
        <button
          type="button"
          onClick={onDelete}
          className="danger-btn"
          disabled={!canDelete}
          title={
            !canDelete
              ? "This section contains built-in fields. Move them elsewhere before deleting."
              : "Delete this section"
          }
        >
          Delete section
        </button>
      </div>

      {section.fields.length === 0 ? (
        <p className="muted" style={{ padding: "12px 14px", margin: 0 }}>
          No fields in this section yet. Add one below or move fields here from
          another section.
        </p>
      ) : (
        <div className="schema-fields-list">
          {section.fields.map((f, i) => (
            <FieldRow
              key={f._key}
              field={f}
              sections={allSections}
              currentSectionId={section.id}
              canMoveUp={i > 0}
              canMoveDown={i < section.fields.length - 1}
              onPatch={(patch) => onPatchField(f._key, patch)}
              onMoveUp={() => onMoveFieldUp(f._key)}
              onMoveDown={() => onMoveFieldDown(f._key)}
              onDelete={() => onDeleteField(f._key)}
              onMoveToSection={(sid) => onMoveFieldToSection(f._key, sid)}
            />
          ))}
        </div>
      )}

      <div className="schema-section-footer">
        {addOpen ? (
          <AddFieldForm
            existingNames={new Set(allSections.flatMap((s) => s.fields.map((f) => f.name)))}
            onCancel={() => setAddOpen(false)}
            onSubmit={(f) => {
              onAddField(f);
              setAddOpen(false);
            }}
          />
        ) : (
          <button type="button" onClick={() => setAddOpen(true)}>
            + Add custom field
          </button>
        )}
      </div>
    </div>
  );
}

function AddFieldForm({
  existingNames,
  onCancel,
  onSubmit,
}: {
  existingNames: Set<string>;
  onCancel: () => void;
  onSubmit: (field: EditorField) => void;
}) {
  const [label, setLabel] = useState("");
  const [name, setName] = useState("");
  const [nameTouched, setNameTouched] = useState(false);
  const [type, setType] = useState<FormFieldType>("text");
  const [required, setRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const suggested = suggestFieldName(label);
  const effectiveName = nameTouched ? name : suggested;

  const validate = (): string | null => {
    if (!label.trim()) return "Label is required.";
    if (!effectiveName) return "Internal name is required.";
    if (!/^[a-z][a-z0-9_]{0,49}$/.test(effectiveName))
      return "Internal name must start with a letter and contain only lowercase letters, digits, and underscores.";
    if (existingNames.has(effectiveName)) return `'${effectiveName}' is already used.`;
    return null;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate();
    if (err) {
      setError(err);
      return;
    }
    const field: EditorField = {
      _key: uniqueKey("field"),
      _isNew: true,
      name: effectiveName,
      label: label.trim(),
      type,
      required: type === "boolean" ? false : required,
      source: "custom",
      options:
        type === "select"
          ? [
              { value: "option_1", label: "Option 1" },
              { value: "option_2", label: "Option 2" },
            ]
          : undefined,
    };
    onSubmit(field);
  };

  return (
    <form className="add-field-form" onSubmit={handleSubmit}>
      <div className="add-field-grid">
        <label className="field" style={{ margin: 0 }}>
          <span className="label" style={{ fontSize: 11 }}>
            Question (what the requester sees)
          </span>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. Cost center"
            autoFocus
          />
        </label>
        <label className="field" style={{ margin: 0 }}>
          <span className="label" style={{ fontSize: 11 }}>
            Internal name (locked after save)
          </span>
          <input
            type="text"
            value={effectiveName}
            onChange={(e) => {
              setNameTouched(true);
              setName(e.target.value);
            }}
            placeholder="cost_center"
            style={{
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            }}
          />
        </label>
        <label className="field" style={{ margin: 0 }}>
          <span className="label" style={{ fontSize: 11 }}>
            Type
          </span>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as FormFieldType)}
          >
            <option value="text">Text — single line</option>
            <option value="textarea">Long text — paragraph</option>
            <option value="select">Dropdown — choose one</option>
            <option value="boolean">Yes / no — checkbox</option>
          </select>
        </label>
        <label
          className="inline-toggle"
          style={{ alignSelf: "end", paddingBottom: 8 }}
        >
          <input
            type="checkbox"
            checked={type === "boolean" ? false : required}
            disabled={type === "boolean"}
            onChange={(e) => setRequired(e.target.checked)}
          />
          <span>Required</span>
        </label>
      </div>
      {error && <div className="error" style={{ marginTop: 8 }}>{error}</div>}
      <div className="form-actions" style={{ marginTop: 8 }}>
        <button type="submit" className="primary">
          Add field
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
