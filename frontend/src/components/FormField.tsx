import type { FormField as FieldDef } from "../types/domain";

interface Props {
  field: FieldDef;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
}

export function FormField({ field, value, onChange, error }: Props) {
  const id = `f-${field.name}`;
  const invalid = Boolean(error);
  const common = {
    id,
    name: field.name,
    "aria-invalid": invalid || undefined,
    "aria-describedby": error ? `${id}-err` : undefined,
  };
  const label = (
    <span className="label">
      {field.label}
      {field.required && (
        <span className="req" aria-hidden="true">
          *
        </span>
      )}
    </span>
  );
  const errorNode = error ? (
    <span id={`${id}-err`} className="field-error" role="alert">
      {error}
    </span>
  ) : null;

  switch (field.type) {
    case "textarea":
      return (
        <label className="field">
          {label}
          <textarea
            {...common}
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            rows={4}
          />
          {errorNode}
        </label>
      );
    case "select":
      return (
        <label className="field">
          {label}
          <select
            {...common}
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
          >
            <option value="">—</option>
            {field.options?.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          {errorNode}
        </label>
      );
    case "boolean":
      return (
        <label className="field" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            {...common}
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
            style={{ width: "auto" }}
          />
          <span>
            {field.label}
            {field.required && (
              <span className="req" aria-hidden="true">
                *
              </span>
            )}
          </span>
          {errorNode}
        </label>
      );
    default:
      return (
        <label className="field">
          {label}
          <input
            {...common}
            type="text"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
          />
          {errorNode}
        </label>
      );
  }
}
