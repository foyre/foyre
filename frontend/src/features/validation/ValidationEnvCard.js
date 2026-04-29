import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { createValidationEnv, downloadKubeconfig, getValidationEnv, teardownValidationEnv, } from "../../api/validationEnvironments";
import { useAuth } from "../../auth/useAuth";
import { KubeconfigCallout } from "./KubeconfigCallout";
const POLL_INTERVAL_MS = 2500;
export function ValidationEnvCard({ request: req, onEnvChanged }) {
    const { user } = useAuth();
    const isOwner = Boolean(user && user.id === req.created_by_id);
    const isAdmin = user?.role === "admin";
    // Admin can create/teardown on any request; kubeconfig is owner-only.
    const canCreate = isOwner || isAdmin;
    const canTeardown = isOwner || isAdmin;
    const canDownload = isOwner;
    const ownerName = req.created_by?.username ?? `user #${req.created_by_id}`;
    const actingOnBehalf = !isOwner && isAdmin;
    const [env, setEnv] = useState(undefined);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [kubeconfig, setKubeconfig] = useState(null);
    const pollRef = useRef(null);
    const stopPolling = () => {
        if (pollRef.current !== null) {
            window.clearInterval(pollRef.current);
            pollRef.current = null;
        }
    };
    useEffect(() => stopPolling, []);
    const refresh = async () => {
        try {
            const next = await getValidationEnv(req.id);
            setEnv(next);
            if (next?.status !== "provisioning")
                stopPolling();
            return next;
        }
        catch (err) {
            setError(apiErrorMessage(err));
            stopPolling();
            return null;
        }
    };
    // First load.
    useEffect(() => {
        refresh().then((e) => {
            if (e?.status === "provisioning")
                startPolling();
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [req.id]);
    const startPolling = () => {
        stopPolling();
        pollRef.current = window.setInterval(refresh, POLL_INTERVAL_MS);
    };
    const onCreate = async () => {
        setBusy(true);
        setError(null);
        try {
            const created = await createValidationEnv(req.id);
            setEnv(created);
            onEnvChanged?.();
            startPolling();
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    const onDownload = async () => {
        setBusy(true);
        setError(null);
        try {
            const k = await downloadKubeconfig(req.id);
            setKubeconfig(k.kubeconfig);
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    const onTeardown = async () => {
        if (!window.confirm("Tear down this validation cluster? This is irreversible."))
            return;
        setBusy(true);
        setError(null);
        try {
            const after = await teardownValidationEnv(req.id);
            setEnv(null); // after teardown, no active env
            onEnvChanged?.();
            setKubeconfig(null);
            // surface last state briefly
            setError(null);
            void after;
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    // Guard: only relevant after the request has been submitted.
    const submittable = req.status !== "draft";
    return (_jsxs("div", { className: "section-block", children: [_jsx("h3", { children: "Validation environment" }), error && _jsx("div", { className: "error", children: error }), kubeconfig && (_jsx(KubeconfigCallout, { kubeconfig: kubeconfig, filename: `vcluster-req-${req.id}.yaml`, onDismiss: () => setKubeconfig(null) })), env === undefined && _jsx("p", { className: "muted", children: "Loading\u2026" }), env === null && (_jsxs("div", { className: "card", children: [actingOnBehalf && (_jsxs("p", { className: "muted", style: { marginTop: 0, fontSize: 13 }, children: ["Acting as admin on behalf of ", _jsx("strong", { children: ownerName }), ". The kubeconfig will still be downloadable only by the request owner."] })), !submittable ? (_jsx("p", { className: "muted", style: { margin: 0 }, children: "Submit the request first to create an isolated validation cluster." })) : canCreate ? (_jsxs(_Fragment, { children: [_jsx("p", { className: "muted", style: { marginTop: 0 }, children: isOwner
                                    ? "Create a dedicated, isolated Kubernetes virtual cluster that you can deploy your application into. The reviewer team will use this to see your deployment running before they approve."
                                    : "Create an isolated validation cluster for this request. The owner will download the kubeconfig to deploy their app." }), _jsx("button", { className: "primary", onClick: onCreate, disabled: busy, children: busy ? "Provisioning…" : "Create isolated cluster" })] })) : (_jsx("p", { className: "muted", style: { margin: 0 }, children: "No validation environment yet." }))] })), env && (_jsx(EnvDetail, { env: env, busy: busy, canDownload: canDownload, canTeardown: canTeardown, actingOnBehalf: actingOnBehalf, ownerName: ownerName, onDownload: onDownload, onTeardown: onTeardown }))] }));
}
function EnvDetail({ env, busy, canDownload, canTeardown, actingOnBehalf, ownerName, onDownload, onTeardown, }) {
    const statusBadge = _jsx("span", { className: "badge", "data-env-status": env.status, children: prettyStatus(env.status) });
    return (_jsxs("div", { className: "card", children: [_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }, children: [statusBadge, env.status === "provisioning" && (_jsx("span", { className: "muted", style: { fontSize: 13 }, children: "This can take up to a few minutes. You can leave and come back." }))] }), _jsxs("dl", { style: {
                    display: "grid",
                    gridTemplateColumns: "max-content 1fr",
                    gap: "4px 16px",
                    marginBottom: 12,
                    fontSize: 14,
                }, children: [_jsx("dt", { className: "muted", children: "Namespace" }), _jsx("dd", { children: _jsx("code", { children: env.namespace }) }), _jsx("dt", { className: "muted", children: "vcluster" }), _jsx("dd", { children: _jsx("code", { children: env.vcluster_name }) }), env.external_endpoint && (_jsxs(_Fragment, { children: [_jsx("dt", { className: "muted", children: "API endpoint" }), _jsx("dd", { children: _jsx("code", { children: env.external_endpoint }) })] })), env.expires_at && (_jsxs(_Fragment, { children: [_jsx("dt", { className: "muted", children: "Expires" }), _jsx("dd", { children: new Date(env.expires_at).toLocaleString() })] }))] }), actingOnBehalf && (_jsxs("p", { className: "muted", style: { margin: "0 0 8px", fontSize: 13 }, children: ["Provisioned for ", _jsx("strong", { children: ownerName }), ". Kubeconfig download is restricted to the request owner."] })), env.status === "ready" && (_jsxs("div", { className: "form-actions", children: [canDownload && (_jsx("button", { className: "primary", onClick: onDownload, disabled: busy, children: busy ? "Working…" : "Download kubeconfig" })), canTeardown && (_jsx("button", { onClick: onTeardown, disabled: busy, children: "Tear down" }))] })), env.status === "failed" && (_jsxs(_Fragment, { children: [env.last_error && (_jsx("pre", { className: "error", style: { whiteSpace: "pre-wrap", marginBottom: 12 }, children: env.last_error })), canTeardown && (_jsx("div", { className: "form-actions", children: _jsx("button", { onClick: onTeardown, disabled: busy, children: "Clean up and retry" }) }))] }))] }));
}
function prettyStatus(s) {
    switch (s) {
        case "provisioning":
            return "Provisioning…";
        case "ready":
            return "Ready";
        case "failed":
            return "Failed";
        case "torn_down":
            return "Torn down";
    }
}
