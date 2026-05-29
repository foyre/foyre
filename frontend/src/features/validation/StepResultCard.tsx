import { useState } from "react";
import { downloadArtifact } from "../../api/validationRuns";
import type { ValidationStepResult } from "../../types/domain";
import {
  SEVERITY_LABEL,
  STEP_STATUS_LABEL,
} from "./validationFormat";

export function StepResultCard({ step }: { step: ValidationStepResult }) {
  const [open, setOpen] = useState(false);
  const findings = step.findings_json ?? [];

  return (
    <div className="step-card">
      <button
        type="button"
        className="step-card-header"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="step-card-caret" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
        <span className="step-card-title">
          {step.display_name || step.step_name}
        </span>
        <span className={`val-badge val-status-${step.status}`}>
          {STEP_STATUS_LABEL[step.status]}
        </span>
        {step.severity !== "none" && (
          <span className={`val-badge val-sev-${step.severity}`}>
            {SEVERITY_LABEL[step.severity]}
          </span>
        )}
      </button>

      {open && (
        <div className="step-card-body">
          {step.summary && <p style={{ marginTop: 0 }}>{step.summary}</p>}
          {step.error_message && (
            <pre className="error" style={{ whiteSpace: "pre-wrap" }}>
              {step.error_message}
            </pre>
          )}

          {findings.length > 0 && (
            <table className="data findings-table">
              <thead>
                <tr>
                  <th style={{ width: 90 }}>Severity</th>
                  <th>Finding</th>
                  <th>Resource</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((f, i) => (
                  <tr key={i}>
                    <td>
                      <span className={`val-badge val-sev-${f.severity}`}>
                        {SEVERITY_LABEL[f.severity]}
                      </span>
                    </td>
                    <td>
                      <strong>{f.title}</strong>
                      {f.message && (
                        <div className="muted" style={{ fontSize: 13 }}>
                          {f.message}
                        </div>
                      )}
                      {f.recommendation && (
                        <div style={{ fontSize: 12, marginTop: 2 }}>
                          ↳ {f.recommendation}
                        </div>
                      )}
                    </td>
                    <td>
                      <code style={{ fontSize: 12 }}>{f.resource ?? "—"}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="step-card-meta muted">
            {step.completed_at && (
              <span>
                Completed {new Date(step.completed_at).toLocaleString()}
              </span>
            )}
          </div>

          {step.artifacts.length > 0 && (
            <div className="step-artifacts">
              <span className="muted" style={{ fontSize: 12 }}>
                Evidence:
              </span>
              {step.artifacts.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  className="artifact-link"
                  onClick={() => downloadArtifact(a)}
                  title={`${a.artifact_type} · ${a.size_bytes} bytes`}
                >
                  ⬇ {a.artifact_name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
