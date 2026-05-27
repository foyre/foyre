import { useState } from "react";
import { FormField } from "../../components/FormField";
import type { FormField as FieldDef } from "../../types/domain";
import type { EditorSection } from "./types";

interface Props {
  sections: EditorSection[];
}

function isVisible(field: FieldDef, values: Record<string, unknown>): boolean {
  if (!field.visible_if) return true;
  return Object.entries(field.visible_if).every(([k, v]) => values[k] === v);
}

/**
 * Renders the live form using the exact same `<FormField />` component
 * requesters will see. Values are kept locally so the admin can play with
 * dropdowns / toggles without touching anything that gets saved.
 */
export function FormPreview({ sections }: Props) {
  const [values, setValues] = useState<Record<string, unknown>>({});

  if (sections.length === 0) {
    return (
      <p className="muted" style={{ padding: 12 }}>
        Add a section to see a preview of the form.
      </p>
    );
  }

  return (
    <div>
      {sections.map((section) => (
        <fieldset key={section._key} className="form-section">
          <legend>{section.title || "(untitled section)"}</legend>
          {section.fields.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>
              No fields yet.
            </p>
          ) : (
            section.fields
              .filter((f) => isVisible(f, values))
              .map((f) => (
                <FormField
                  key={f._key}
                  field={f}
                  value={values[f.name]}
                  onChange={(v) => setValues((prev) => ({ ...prev, [f.name]: v }))}
                />
              ))
          )}
        </fieldset>
      ))}
    </div>
  );
}
