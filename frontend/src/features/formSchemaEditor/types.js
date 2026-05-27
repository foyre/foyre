let _idSeq = 0;
export function uniqueKey(prefix = "k") {
    _idSeq += 1;
    return `${prefix}_${Date.now().toString(36)}_${_idSeq}`;
}
export function toEditor(sections) {
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
export function toApi(sections) {
    return sections.map((s) => ({
        id: s.id,
        title: s.title,
        fields: s.fields.map((f) => {
            const out = {
                name: f.name,
                label: f.label,
                type: f.type,
            };
            if (f.required)
                out.required = true;
            if (f.options && f.options.length > 0)
                out.options = f.options;
            if (f.visible_if)
                out.visible_if = f.visible_if;
            return out;
        }),
    }));
}
/**
 * Generate a section id from its title (used only for new sections). Falls
 * back to a random suffix if the title gives nothing usable.
 */
export function generateSectionId(title) {
    const slug = title
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "")
        .slice(0, 50);
    if (slug)
        return slug;
    return `section_${Math.random().toString(36).slice(2, 8)}`;
}
/** Suggest a field name from a label; same slug rules as the backend. */
export function suggestFieldName(label) {
    return label
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "")
        .slice(0, 50);
}
