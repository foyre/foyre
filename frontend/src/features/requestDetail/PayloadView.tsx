import type { FormSchema } from "../../types/domain";

interface Props {
  schema: FormSchema;
  payload: Record<string, unknown>;
}

function formatValue(v: unknown): { text: string; unset: boolean } {
  if (v === undefined || v === null || v === "") return { text: "—", unset: true };
  if (typeof v === "boolean") return { text: v ? "Yes" : "No", unset: false };
  return { text: String(v), unset: false };
}

/**
 * Read-only, section-grouped render of a payload using the form schema's
 * section/field layout. Fields missing from the payload render as "—" so
 * reviewers see what's unanswered vs. what's explicitly blank.
 *
 * If the request payload carries keys that don't appear in the current
 * schema (e.g. an admin removed a custom field after the request was
 * created), we surface them under "Other answers" so the data isn't
 * silently dropped from the UI.
 */
export function PayloadView({ schema, payload }: Props) {
  const knownNames = new Set<string>();
  for (const s of schema.sections) {
    for (const f of s.fields) knownNames.add(f.name);
  }
  const orphanEntries = Object.entries(payload).filter(
    ([k]) => !knownNames.has(k),
  );

  return (
    <div>
      {schema.sections.map((section) => (
        <div key={section.id} className="payload-section">
          <h4>{section.title}</h4>
          <dl>
            {section.fields.map((f) => {
              const { text, unset } = formatValue(payload[f.name]);
              return (
                <div key={f.name} style={{ display: "contents" }}>
                  <dt>{f.label}</dt>
                  <dd className={unset ? "unset" : undefined}>{text}</dd>
                </div>
              );
            })}
          </dl>
        </div>
      ))}
      {orphanEntries.length > 0 && (
        <div className="payload-section">
          <h4 title="These answers were captured under field names that are no longer part of the intake form. Likely the admin removed the field after this request was created.">
            Other answers (no longer in form)
          </h4>
          <dl>
            {orphanEntries.map(([k, v]) => {
              const { text, unset } = formatValue(v);
              return (
                <div key={k} style={{ display: "contents" }}>
                  <dt>
                    <code>{k}</code>
                  </dt>
                  <dd className={unset ? "unset" : undefined}>{text}</dd>
                </div>
              );
            })}
          </dl>
        </div>
      )}
    </div>
  );
}
