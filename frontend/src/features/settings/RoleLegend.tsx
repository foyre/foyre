import { useState } from "react";
import { ROLE_DESCRIPTIONS, ROLE_ORDER } from "./roleDescriptions";

export function RoleLegend() {
  const [open, setOpen] = useState(false);
  return (
    <div className="card" style={{ marginBottom: 16, padding: "12px 16px" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        style={{
          background: "transparent",
          border: "none",
          padding: 0,
          cursor: "pointer",
          color: "var(--accent)",
          fontWeight: 500,
        }}
      >
        {open ? "\u25BE" : "\u25B8"} What can each role do?
      </button>

      {open && (
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "max-content 1fr",
            gap: "10px 16px",
            margin: "12px 0 0",
          }}
        >
          {ROLE_ORDER.map((r) => {
            const info = ROLE_DESCRIPTIONS[r];
            return (
              <div key={r} style={{ display: "contents" }}>
                <dt style={{ fontWeight: 500 }}>{info.label}</dt>
                <dd style={{ margin: 0 }}>
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    {info.bullets.map((b, i) => (
                      <li key={i}>{b}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            );
          })}
        </dl>
      )}
    </div>
  );
}
