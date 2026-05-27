import type { FormField, FormSection } from "../../types/domain";

/**
 * Editor-only superset of a field. `_isNew` distinguishes fields the admin
 * just added (where they can still change the `name` + `type`) from fields
 * that already exist in the saved schema (where those are locked).
 */
export interface EditorField extends FormField {
  _key: string;
  _isNew?: boolean;
}

export interface EditorSection extends Omit<FormSection, "fields"> {
  _key: string;
  fields: EditorField[];
}

let _idSeq = 0;
export function uniqueKey(prefix = "k"): string {
  _idSeq += 1;
  return `${prefix}_${Date.now().toString(36)}_${_idSeq}`;
}

export function toEditor(sections: FormSection[]): EditorSection[] {
  return sections.map((s) => ({
    ...s,
    _key: uniqueKey("section"),
    fields: s.fields.map((f) => ({
      ...f,
      _key: uniqueKey("field"),
    })),
  }));
}

/** Strip editor-only flags before sending to the API. */
export function toApi(sections: EditorSection[]): FormSection[] {
  return sections.map((s) => ({
    id: s.id,
    title: s.title,
    fields: s.fields.map((f) => {
      const out: FormField = {
        name: f.name,
        label: f.label,
        type: f.type,
      };
      if (f.required) out.required = true;
      if (f.options && f.options.length > 0) out.options = f.options;
      if (f.visible_if) out.visible_if = f.visible_if;
      return out;
    }),
  }));
}

/**
 * Generate a section id from its title (used only for new sections). Falls
 * back to a random suffix if the title gives nothing usable.
 */
export function generateSectionId(title: string): string {
  const slug = title
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 50);
  if (slug) return slug;
  return `section_${Math.random().toString(36).slice(2, 8)}`;
}

/** Suggest a field name from a label; same slug rules as the backend. */
export function suggestFieldName(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 50);
}
