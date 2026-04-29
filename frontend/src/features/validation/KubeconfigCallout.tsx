import { useState } from "react";

interface Props {
  kubeconfig: string;
  filename?: string;
  onDismiss: () => void;
}

/**
 * Post-download callout that shows the kubeconfig once. Offers copy-to-clipboard
 * and direct download as a .yaml file. Once dismissed, the requester must hit
 * the kubeconfig endpoint again to see it.
 */
export function KubeconfigCallout({ kubeconfig, filename = "kubeconfig.yaml", onDismiss }: Props) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(kubeconfig);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* insecure context; admin can select manually */
    }
  };

  const download = () => {
    const blob = new Blob([kubeconfig], { type: "application/x-yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <strong>Kubeconfig for your validation cluster</strong>
          <p className="muted" style={{ margin: "6px 0 10px" }}>
            Save this file and use it with <code>kubectl</code> / <code>helm</code> to
            deploy your application. Don't share it — it grants full access to
            your isolated cluster.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" className="primary" onClick={download}>
              Download .yaml
            </button>
            <button type="button" onClick={copy}>
              {copied ? "Copied" : "Copy to clipboard"}
            </button>
          </div>
          <details style={{ marginTop: 10 }}>
            <summary className="muted" style={{ cursor: "pointer", fontSize: 13 }}>
              Preview contents
            </summary>
            <pre
              style={{
                background: "white",
                border: "1px solid var(--border)",
                padding: 10,
                borderRadius: "var(--radius)",
                maxHeight: 260,
                overflow: "auto",
                fontSize: 11,
                userSelect: "all",
              }}
            >
              {kubeconfig}
            </pre>
          </details>
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
