import { useState } from "react";
import type { FormFieldType } from "../../types/domain";
import type { EditorField, EditorSection } from "./types";

interface Props {
  field: EditorField;
  sections: EditorSection[];
  currentSectionId: string;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onPatch: (patch: Partial<EditorField>) => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onDelete: () => void;
  onMoveToSection: (sectionId: string) => void;
}

const TYPE_LABEL: Record<FormFieldType, string> = {
  text: "Text",
  textarea: "Long text",
  select: "Dropdown",
  boolean: "Yes / no",
};

export function FieldRow({
  field,
  sections,
  currentSectionId,
  canMoveUp,
  canMoveDown,
  onPatch,
  onMoveUp,
  onMoveDown,
  onDelete,
  onMoveToSection,
}: Props) {
  const isCore = field.source === "core";
  const isNew = !!field._isNew;
  const isSelect = field.type === "select";
  const [optionsOpen, setOptionsOpen] = useState(false);

  // Backend allows admins to relabel core fields but NOT change anything
  // else; we mirror that here.
  return (
    <div className="schema-field">
      <div className="schema-field-main">
        <div className="schema-field-reorder">
          <button
            type="button"
            className="icon-btn"
            onClick={onMoveUp}
            disabled={!canMoveUp}
            title="Move up"
            aria-label="Move field up"
          >
            ↑
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={onMoveDown}
            disabled={!canMoveDown}
            title="Move down"
            aria-label="Move field down"
          >
            ↓
          </button>
        </div>

        <div className="schema-field-body">
          <div className="schema-field-headline">
            <span
              className={`field-source-pill ${isCore ? "is-core" : "is-custom"}`}
            >
              {isCore ? "Built-in" : "Custom"}
            </span>
            <span className="field-type-pill">{TYPE_LABEL[field.type]}</span>
            <code className="field-name-mono">{field.name}</code>
            {field.required && (
              <span className="field-req-pill" title="Required">
                Required
              </span>
            )}
          </div>

          <label className="field" style={{ marginBottom: 0, marginTop: 6 }}>
            <span className="label" style={{ fontSize: 11 }}>
              Question shown to requester
            </span>
            <input
              type="text"
              value={field.label}
              onChange={(e) => onPatch({ label: e.target.value })}
              placeholder="Field label"
            />
          </label>

          {isNew && !isCore && (
            <div className="schema-field-extras">
              <label className="field" style={{ marginBottom: 0 }}>
                <span className="label" style={{ fontSize: 11 }}>
                  Internal name
                </span>
                <input
                  type="text"
                  value={field.name}
                  onChange={(e) => onPatch({ name: e.target.value })}
                  placeholder="cost_center"
                  style={{
                    fontFamily:
                      "ui-monospace, SFMono-Regular, Menlo, monospace",
                  }}
                />
                <span className="muted" style={{ fontSize: 11 }}>
                  Lowercase, digits, underscores. Locked after first save.
                </span>
              </label>
              <label className="field" style={{ marginBottom: 0 }}>
                <span className="label" style={{ fontSize: 11 }}>
                  Type
                </span>
                <select
                  value={field.type}
                  onChange={(e) => {
                    const newType = e.target.value as FormFieldType;
                    const patch: Partial<EditorField> = { type: newType };
                    if (newType === "select" && !field.options) {
                      patch.options = [{ value: "option_1", label: "Option 1" }];
                    } else if (newType !== "select") {
                      patch.options = undefined;
                    }
                    onPatch(patch);
                  }}
                >
                  <option value="text">Text — single line</option>
                  <option value="textarea">Long text — paragraph</option>
                  <option value="select">Dropdown — choose one</option>
                  <option value="boolean">Yes / no — checkbox</option>
                </select>
              </label>
            </div>
          )}
        </div>
      </div>

      <div className="schema-field-controls">
        {!isCore && (
          <label
            className="inline-toggle"
            title={
              field.type === "boolean"
                ? "Booleans default to false; 'required' has no effect."
                : "Force the requester to fill this in before submitting."
            }
          >
            <input
              type="checkbox"
              checked={!!field.required}
              onChange={(e) => onPatch({ required: e.target.checked })}
              disabled={field.type === "boolean"}
            />
            <span>Required</span>
          </label>
        )}

        {sections.length > 1 && (
          <select
            value={currentSectionId}
            onChange={(e) => onMoveToSection(e.target.value)}
            title="Move this field into a different section"
            className="schema-section-select"
          >
            {sections.map((s) => (
              <option key={s._key} value={s.id}>
                Section: {s.title || "(untitled)"}
              </option>
            ))}
          </select>
        )}

        {isSelect && (
          <button
            type="button"
            onClick={() => setOptionsOpen((v) => !v)}
            disabled={isCore}
            title={
              isCore
                ? "Built-in select options are tied to backend logic and can't be changed."
                : "Edit dropdown options"
            }
          >
            {optionsOpen ? "Close options" : `Options (${field.options?.length ?? 0})`}
          </button>
        )}

        {!isCore && (
          <button
            type="button"
            onClick={onDelete}
            className="danger-btn"
            title="Remove this custom field. Existing answers will become orphan data."
          >
            Remove
          </button>
        )}
      </div>

      {isSelect && optionsOpen && !isCore && (
        <OptionsEditor
          options={field.options ?? []}
          onChange={(options) => onPatch({ options })}
        />
      )}
    </div>
  );
}

function OptionsEditor({
  options,
  onChange,
}: {
  options: { value: string; label: string }[];
  onChange: (options: { value: string; label: string }[]) => void;
}) {
  return (
    <div className="schema-options-editor">
      <div className="schema-options-header">
        <span className="muted" style={{ fontSize: 12 }}>
          Internal value
        </span>
        <span className="muted" style={{ fontSize: 12 }}>
          Label shown to requester
        </span>
        <span />
      </div>
      {options.map((opt, i) => (
        <div key={i} className="schema-option-row">
          <input
            type="text"
            value={opt.value}
            onChange={(e) => {
              const next = [...options];
              next[i] = { ...opt, value: e.target.value };
              onChange(next);
            }}
            placeholder="value"
            style={{
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            }}
          />
          <input
            type="text"
            value={opt.label}
            onChange={(e) => {
              const next = [...options];
              next[i] = { ...opt, label: e.target.value };
              onChange(next);
            }}
            placeholder="Display label"
          />
          <button
            type="button"
            onClick={() => onChange(options.filter((_, j) => j !== i))}
            disabled={options.length <= 1}
            title={
              options.length <= 1
                ? "A dropdown needs at least one option."
                : "Remove this option"
            }
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() =>
          onChange([
            ...options,
            { value: `option_${options.length + 1}`, label: `Option ${options.length + 1}` },
          ])
        }
      >
        Add option
      </button>
    </div>
  );
}
