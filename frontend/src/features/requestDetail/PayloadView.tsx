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
 */
export function PayloadView({ schema, payload }: Props) {
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
    </div>
  );
}
