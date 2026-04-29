import { useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import {
  type ValidationEnvironment,
  createValidationEnv,
  downloadKubeconfig,
  getValidationEnv,
  teardownValidationEnv,
} from "../../api/validationEnvironments";
import { useAuth } from "../../auth/useAuth";
import type { IntakeRequest } from "../../types/domain";
import { KubeconfigCallout } from "./KubeconfigCallout";

interface Props {
  request: IntakeRequest;
  /** Callback so the parent can refresh history after env events. */
  onEnvChanged?: () => void;
}

const POLL_INTERVAL_MS = 2500;

export function ValidationEnvCard({ request: req, onEnvChanged }: Props) {
  const { user } = useAuth();
  const isOwner = Boolean(user && user.id === req.created_by_id);
  const isAdmin = user?.role === "admin";
  // Admin can create/teardown on any request; kubeconfig is owner-only.
  const canCreate = isOwner || isAdmin;
  const canTeardown = isOwner || isAdmin;
  const canDownload = isOwner;
  const ownerName =
    req.created_by?.username ?? `user #${req.created_by_id}`;
  const actingOnBehalf = !isOwner && isAdmin;

  const [env, setEnv] = useState<ValidationEnvironment | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [kubeconfig, setKubeconfig] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

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
      if (next?.status !== "provisioning") stopPolling();
      return next;
    } catch (err) {
      setError(apiErrorMessage(err));
      stopPolling();
      return null;
    }
  };

  // First load.
  useEffect(() => {
    refresh().then((e) => {
      if (e?.status === "provisioning") startPolling();
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
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const onDownload = async () => {
    setBusy(true);
    setError(null);
    try {
      const k = await downloadKubeconfig(req.id);
      setKubeconfig(k.kubeconfig);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const onTeardown = async () => {
    if (!window.confirm("Tear down this validation cluster? This is irreversible.")) return;
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
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  // Guard: only relevant after the request has been submitted.
  const submittable = req.status !== "draft";

  return (
    <div className="section-block">
      <h3>Validation environment</h3>

      {error && <div className="error">{error}</div>}

      {kubeconfig && (
        <KubeconfigCallout
          kubeconfig={kubeconfig}
          filename={`vcluster-req-${req.id}.yaml`}
          onDismiss={() => setKubeconfig(null)}
        />
      )}

      {env === undefined && <p className="muted">Loading…</p>}

      {env === null && (
        <div className="card">
          {actingOnBehalf && (
            <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
              Acting as admin on behalf of <strong>{ownerName}</strong>. The
              kubeconfig will still be downloadable only by the request owner.
            </p>
          )}
          {!submittable ? (
            <p className="muted" style={{ margin: 0 }}>
              Submit the request first to create an isolated validation cluster.
            </p>
          ) : canCreate ? (
            <>
              <p className="muted" style={{ marginTop: 0 }}>
                {isOwner
                  ? "Create a dedicated, isolated Kubernetes virtual cluster that you can deploy your application into. The reviewer team will use this to see your deployment running before they approve."
                  : "Create an isolated validation cluster for this request. The owner will download the kubeconfig to deploy their app."}
              </p>
              <button className="primary" onClick={onCreate} disabled={busy}>
                {busy ? "Provisioning…" : "Create isolated cluster"}
              </button>
            </>
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              No validation environment yet.
            </p>
          )}
        </div>
      )}

      {env && (
        <EnvDetail
          env={env}
          busy={busy}
          canDownload={canDownload}
          canTeardown={canTeardown}
          actingOnBehalf={actingOnBehalf}
          ownerName={ownerName}
          onDownload={onDownload}
          onTeardown={onTeardown}
        />
      )}
    </div>
  );
}

function EnvDetail({
  env,
  busy,
  canDownload,
  canTeardown,
  actingOnBehalf,
  ownerName,
  onDownload,
  onTeardown,
}: {
  env: ValidationEnvironment;
  busy: boolean;
  canDownload: boolean;
  canTeardown: boolean;
  actingOnBehalf: boolean;
  ownerName: string;
  onDownload: () => void;
  onTeardown: () => void;
}) {
  const statusBadge = <span className="badge" data-env-status={env.status}>{prettyStatus(env.status)}</span>;

  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        {statusBadge}
        {env.status === "provisioning" && (
          <span className="muted" style={{ fontSize: 13 }}>
            This can take up to a few minutes. You can leave and come back.
          </span>
        )}
      </div>

      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "max-content 1fr",
          gap: "4px 16px",
          marginBottom: 12,
          fontSize: 14,
        }}
      >
        <dt className="muted">Namespace</dt>
        <dd>
          <code>{env.namespace}</code>
        </dd>
        <dt className="muted">vcluster</dt>
        <dd>
          <code>{env.vcluster_name}</code>
        </dd>
        {env.external_endpoint && (
          <>
            <dt className="muted">API endpoint</dt>
            <dd>
              <code>{env.external_endpoint}</code>
            </dd>
          </>
        )}
        {env.expires_at && (
          <>
            <dt className="muted">Expires</dt>
            <dd>{new Date(env.expires_at).toLocaleString()}</dd>
          </>
        )}
      </dl>

      {actingOnBehalf && (
        <p className="muted" style={{ margin: "0 0 8px", fontSize: 13 }}>
          Provisioned for <strong>{ownerName}</strong>. Kubeconfig download is
          restricted to the request owner.
        </p>
      )}

      {env.status === "ready" && (
        <div className="form-actions">
          {canDownload && (
            <button className="primary" onClick={onDownload} disabled={busy}>
              {busy ? "Working…" : "Download kubeconfig"}
            </button>
          )}
          {canTeardown && (
            <button onClick={onTeardown} disabled={busy}>
              Tear down
            </button>
          )}
        </div>
      )}

      {env.status === "failed" && (
        <>
          {env.last_error && (
            <pre
              className="error"
              style={{ whiteSpace: "pre-wrap", marginBottom: 12 }}
            >
              {env.last_error}
            </pre>
          )}
          {canTeardown && (
            <div className="form-actions">
              <button onClick={onTeardown} disabled={busy}>
                Clean up and retry
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function prettyStatus(s: ValidationEnvironment["status"]): string {
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
