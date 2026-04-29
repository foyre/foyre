import { useState } from "react";

export interface NewUserInfo {
  username: string;
  tempPassword: string;
  mustChangeOnLogin: boolean;
}

interface Props {
  info: NewUserInfo;
  onDismiss: () => void;
}

export function NewUserCallout({ info, onDismiss }: Props) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(info.tempPassword);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Older browsers / insecure context: leave the password visible; the
      // admin can select-and-copy manually.
    }
  };

  return (
    <div
      role="status"
      className="card"
      style={{
        borderColor: "#a7f3d0",
        background: "#ecfdf5",
        marginBottom: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 12,
        }}
      >
        <div style={{ flex: 1 }}>
          <strong>User "{info.username}" created.</strong>
          <p className="muted" style={{ margin: "6px 0 10px" }}>
            Share the temporary password below with the user out-of-band (chat,
            phone, etc.). This is the only time it will be shown.
            {info.mustChangeOnLogin && (
              <> They'll be required to change it on first login.</>
            )}
          </p>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            <code
              style={{
                background: "white",
                border: "1px solid var(--border)",
                padding: "6px 10px",
                borderRadius: "var(--radius)",
                fontSize: 14,
                fontFamily:
                  "ui-monospace, SFMono-Regular, Menlo, monospace",
                userSelect: "all",
              }}
            >
              {info.tempPassword}
            </code>
            <button type="button" onClick={copy}>
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          title="Dismiss"
          style={{ padding: "2px 8px" }}
        >
          ×
        </button>
      </div>
    </div>
  );
}
