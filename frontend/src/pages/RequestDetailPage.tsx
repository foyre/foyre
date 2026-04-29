import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiErrorMessage } from "../api/errors";
import { getFormSchema } from "../api/meta";
import { changeStatus, getRequest, submitRequest } from "../api/requests";
import { useAuth } from "../auth/useAuth";
import { RiskBadge } from "../components/RiskBadge";
import { StatusBadge } from "../components/StatusBadge";
import { CommentComposer } from "../features/comments/CommentComposer";
import { CommentList } from "../features/comments/CommentList";
import { HistoryList } from "../features/history/HistoryList";
import { PayloadView } from "../features/requestDetail/PayloadView";
import { availableTransitions } from "../features/requestActions";
import { ValidationEnvCard } from "../features/validation/ValidationEnvCard";
import {
  type FormSchema,
  type IntakeRequest,
  type RequestStatus,
  isPrivileged,
} from "../types/domain";

export function RequestDetailPage() {
  const { id } = useParams();
  const reqId = Number(id);
  const { user } = useAuth();

  const [req, setReq] = useState<IntakeRequest | null>(null);
  const [schema, setSchema] = useState<FormSchema | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    Promise.all([getRequest(reqId), getFormSchema()])
      .then(([r, s]) => {
        setReq(r);
        setSchema(s);
      })
      .catch((e) => setError(apiErrorMessage(e)));
  }, [reqId]);

  if (error) return <div className="error">{error}</div>;
  if (!req || !schema || !user) return <p className="muted">Loading…</p>;

  const isOwner = req.created_by_id === user.id;
  const canReview = isPrivileged(user.role);
  const canComment = canReview;
  const actions = availableTransitions(req.status, user.role);

  const runAction = async (fn: () => Promise<IntakeRequest>) => {
    setBusy(true);
    setError(null);
    try {
      const updated = await fn();
      setReq(updated);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const appName =
    (req.payload as { application_name?: string }).application_name ||
    "(untitled)";

  return (
    <section>
      <div className="header-row">
        <div>
          <h2 style={{ marginBottom: 4 }}>
            {appName}{" "}
            <span className="muted" style={{ fontWeight: 400 }}>
              #{req.id}
            </span>
          </h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <StatusBadge status={req.status} />
            <RiskBadge level={req.risk_level} />
          </div>
        </div>
        {isOwner && req.status === "draft" && (
          <Link to={`/requests/${req.id}/edit`}>
            <button>Edit draft</button>
          </Link>
        )}
      </div>

      <dl className="meta">
        <dt>Requester</dt>
        <dd>
          {req.created_by?.username ?? `#${req.created_by_id}`}
          {req.created_by && (
            <span className="muted"> · {req.created_by.role}</span>
          )}
        </dd>
        <dt>Created</dt>
        <dd>{new Date(req.created_at).toLocaleString()}</dd>
        <dt>Updated</dt>
        <dd>{new Date(req.updated_at).toLocaleString()}</dd>
      </dl>

      {req.risk_reasons && req.risk_reasons.length > 0 && (
        <div className="payload-section">
          <h4>Risk reasons</h4>
          <div style={{ padding: "12px 14px" }}>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {req.risk_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {isOwner && req.status === "draft" && (
        <div className="form-actions" style={{ marginBottom: 16 }}>
          <button
            className="primary"
            disabled={busy}
            onClick={() => runAction(() => submitRequest(req.id))}
          >
            Submit for review
          </button>
        </div>
      )}

      {(isOwner || user.role === "admin") && req.status === "submitted" && (
        <div className="form-actions" style={{ marginBottom: 16 }}>
          <button
            className="primary"
            disabled={busy}
            onClick={() =>
              runAction(() => changeStatus(req.id, "ready_for_review"))
            }
          >
            Mark ready for review
          </button>
          <span className="muted" style={{ fontSize: 13 }}>
            Signals to reviewers that you've deployed into your validation
            cluster and are ready for feedback.
          </span>
        </div>
      )}

      {(isOwner || user.role === "admin") && req.status === "ready_for_review" && (
        <div className="form-actions" style={{ marginBottom: 16 }}>
          <button
            disabled={busy}
            onClick={() => runAction(() => changeStatus(req.id, "submitted"))}
          >
            Move back to submitted
          </button>
          <span className="muted" style={{ fontSize: 13 }}>
            Use this if you need to keep working before reviewers look.
          </span>
        </div>
      )}

      {canReview && actions.length > 0 && (
        <div className="form-actions" style={{ marginBottom: 16 }}>
          {actions.map((a) => (
            <button
              key={a.to}
              className={a.kind === "primary" ? "primary" : undefined}
              disabled={busy}
              onClick={() =>
                runAction(() => changeStatus(req.id, a.to as RequestStatus))
              }
            >
              {a.label}
            </button>
          ))}
        </div>
      )}

      <div className="section-block">
        <h3>Request details</h3>
        <PayloadView schema={schema} payload={req.payload} />
      </div>

      {(isOwner || user.role === "admin") && (
        <ValidationEnvCard
          request={req}
          onEnvChanged={() => setReloadKey((k) => k + 1)}
        />
      )}

      <div className="section-block">
        <h3>Comments</h3>
        <CommentList requestId={req.id} reloadKey={reloadKey} />
        {canComment && (
          <CommentComposer
            requestId={req.id}
            onPosted={() => setReloadKey((k) => k + 1)}
          />
        )}
      </div>

      <div className="section-block">
        <h3>History</h3>
        <HistoryList requestId={req.id} reloadKey={reloadKey} />
      </div>
    </section>
  );
}
