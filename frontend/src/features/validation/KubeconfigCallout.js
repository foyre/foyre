import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
/**
 * Post-download callout that shows the kubeconfig once. Offers copy-to-clipboard
 * and direct download as a .yaml file. Once dismissed, the requester must hit
 * the kubeconfig endpoint again to see it.
 */
export function KubeconfigCallout({ kubeconfig, filename = "kubeconfig.yaml", onDismiss }) {
    const [copied, setCopied] = useState(false);
    const copy = async () => {
        try {
            await navigator.clipboard.writeText(kubeconfig);
            setCopied(true);
            window.setTimeout(() => setCopied(false), 2000);
        }
        catch {
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
    return (_jsx("div", { role: "status", className: "card", style: {
            borderColor: "#a7f3d0",
            background: "#ecfdf5",
            marginBottom: 16,
        }, children: _jsxs("div", { style: { display: "flex", justifyContent: "space-between", gap: 12 }, children: [_jsxs("div", { style: { flex: 1 }, children: [_jsx("strong", { children: "Kubeconfig for your validation cluster" }), _jsxs("p", { className: "muted", style: { margin: "6px 0 10px" }, children: ["Save this file and use it with ", _jsx("code", { children: "kubectl" }), " / ", _jsx("code", { children: "helm" }), " to deploy your application. Don't share it \u2014 it grants full access to your isolated cluster."] }), _jsxs("div", { style: { display: "flex", gap: 8, flexWrap: "wrap" }, children: [_jsx("button", { type: "button", className: "primary", onClick: download, children: "Download .yaml" }), _jsx("button", { type: "button", onClick: copy, children: copied ? "Copied" : "Copy to clipboard" })] }), _jsxs("details", { style: { marginTop: 10 }, children: [_jsx("summary", { className: "muted", style: { cursor: "pointer", fontSize: 13 }, children: "Preview contents" }), _jsx("pre", { style: {
                                        background: "white",
                                        border: "1px solid var(--border)",
                                        padding: 10,
                                        borderRadius: "var(--radius)",
                                        maxHeight: 260,
                                        overflow: "auto",
                                        fontSize: 11,
                                        userSelect: "all",
                                    }, children: kubeconfig })] })] }), _jsx("button", { type: "button", onClick: onDismiss, "aria-label": "Dismiss", title: "Dismiss", style: { padding: "2px 8px" }, children: "\u00D7" })] }) }));
}
