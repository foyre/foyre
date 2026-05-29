import { useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { listPipelines } from "../../api/validationPipelines";
import {
  getValidationRun,
  listValidationRuns,
  startValidationRun,
} from "../../api/validationRuns";
import { useAuth } from "../../auth/useAuth";
import {
  type IntakeRequest,
  type PipelineSummary,
  type ValidationRun,
  isPrivileged,
} from "../../types/domain";
import { StepResultCard } from "./StepResultCard";
import { IMPACT_LABEL, RUN_STATUS_LABEL, isTerminal } from "./validationFormat";

interface Props {
  request: IntakeRequest;
  /** Bumped by the parent to force a reload (e.g. after env changes). */
  reloadKey?: number;
  /** Called whenever a run completes so the parent can refresh history/gate. */
  onRunChanged?: () => void;
}

const POLL_MS = 3000;

export function ValidationRunsPanel({ request: req, reloadKey, onRunChanged }: Props) {
  const { user } = useAuth();
  const canRun = Boolean(user && isPrivileged(user.role));

  const [latest, setLatest] = useState<ValidationRun | null | undefined>(undefined);
  const [pipelines, setPipelines] = useState<PipelineSummary[]>([]);
  const [pipelineId, setPipelineId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };
  useEffect(() => stopPolling, []);

  const loadLatest = async () => {
    try {
      const runs = await listValidationRuns(req.id);
      if (runs.length === 0) {
        setLatest(null);
        return null;
      }
      const full = await getValidationRun(runs[0].id);
      setLatest(full);
      if (isTerminal(full.status)) {
        stopPolling();
        onRunChanged?.();
      }
      return full;
    } catch (err) {
      setError(apiErrorMessage(err));
      stopPolling();
      return null;
    }
  };

  useEffect(() => {
    loadLatest().then((run) => {
      if (run && !isTerminal(run.status)) startPolling();
    });
    if (canRun) {
      listPipelines()
        .then((ps) => setPipelines(ps.filter((p) => p.enabled)))
        .catch(() => setPipelines([]));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [req.id, reloadKey]);

  const startPolling = () => {
    stopPolling();
    pollRef.current = window.setInterval(loadLatest, POLL_MS);
  };

  const onRun = async () => {
    setBusy(true);
    setError(null);
    try {
      const run = await startValidationRun(req.id, {
        pipeline_id: pipelineId === "" ? null : pipelineId,
      });
      setLatest(run);
      onRunChanged?.();
      startPolling();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  // Only meaningful once the request has progressed past draft.
  if (req.status === "draft") return null;

  const defaultPipeline = pipelines.find((p) => p.is_default);

  return (
    <div className="section-block">
      <h3>Validation pipeline</h3>
      {error && <div className="error">{error}</div>}

      {canRun && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            {pipelines.length > 1 && (
              <select
                value={pipelineId}
                onChange={(e) =>
                  setPipelineId(e.target.value === "" ? "" : Number(e.target.value))
                }
                style={{ maxWidth: 320 }}
              >
                <option value="">
                  Default{defaultPipeline ? `: ${defaultPipeline.display_name}` : ""}
                </option>
                {pipelines.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.display_name}
                  </option>
                ))}
              </select>
            )}
            <button className="primary" onClick={onRun} disabled={busy}>
              {busy ? "Starting…" : "Run validation pipeline"}
            </button>
            <span className="muted" style={{ fontSize: 13 }}>
              Runs against this request's validation environment.
            </span>
          </div>
        </div>
      )}

      {latest === undefined && <p className="muted">Loading…</p>}

      {latest === null && (
        <div className="empty">
          No validation runs yet.
          {canRun
            ? " Run a pipeline to collect evidence before approval."
            : " A reviewer can run a pipeline to collect evidence."}
        </div>
      )}

      {latest && <RunView run={latest} />}
    </div>
  );
}

function RunView({ run }: { run: ValidationRun }) {
  const summary = run.summary_json ?? {};
  const stepCounts = (summary.stepStatusCounts ?? {}) as Record<string, number>;
  const countsText = Object.entries(stepCounts)
    .map(([k, v]) => `${v} ${k}`)
    .join(", ");

  return (
    <div className="card">
      <div className="run-header">
        <div>
          <div className="run-pipeline-name">{run.pipeline_name}</div>
          <div className="muted" style={{ fontSize: 12 }}>
            v{run.pipeline_version} · started {new Date(run.started_at).toLocaleString()}
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span className={`val-badge val-status-${run.status}`}>
            {RUN_STATUS_LABEL[run.status]}
          </span>
          <span className={`val-badge val-impact-${run.approval_impact}`}>
            Approval: {IMPACT_LABEL[run.approval_impact]}
          </span>
        </div>
      </div>

      {countsText && (
        <p className="muted" style={{ fontSize: 13, margin: "4px 0 12px" }}>
          Checks: {countsText}
        </p>
      )}

      {run.error_message && (
        <pre className="error" style={{ whiteSpace: "pre-wrap" }}>
          {run.error_message}
        </pre>
      )}

      <div className="step-cards">
        {run.step_results.map((s) => (
          <StepResultCard key={s.id} step={s} />
        ))}
      </div>
    </div>
  );
}
