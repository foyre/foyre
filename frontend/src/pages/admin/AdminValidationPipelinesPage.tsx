import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import {
  deletePipeline,
  getPipeline,
  listPipelines,
  setDefaultPipeline,
  updatePipeline,
} from "../../api/validationPipelines";
import type { Pipeline, PipelineSummary } from "../../types/domain";
import { PipelineEditor } from "../../features/validationPipelines/PipelineEditor";
import { PolicyControls } from "../../features/validationPipelines/PolicyControls";

type EditorState =
  | { mode: "closed" }
  | { mode: "create" }
  | { mode: "edit"; pipeline: Pipeline };

export function AdminValidationPipelinesPage() {
  const [pipelines, setPipelines] = useState<PipelineSummary[] | null>(null);
  const [editor, setEditor] = useState<EditorState>({ mode: "closed" });
  const [error, setError] = useState<string | null>(null);

  const reload = async () => {
    try {
      setPipelines(await listPipelines());
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  };

  useEffect(() => {
    reload();
  }, []);

  const guarded = async (fn: () => Promise<void>) => {
    setError(null);
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  };

  const openEdit = async (id: number) => {
    setError(null);
    try {
      const full = await getPipeline(id);
      setEditor({ mode: "edit", pipeline: full });
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  };

  return (
    <div>
      <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
        Define reusable validation pipelines that reviewers run against a
        request's validation environment. Pipelines collect evidence
        (workload inventory, security posture, image scans, custom checks)
        before approval.
      </p>

      <PolicyControls />

      {error && <div className="error">{error}</div>}

      <div className="header-row" style={{ marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Pipelines</h3>
        {editor.mode === "closed" && (
          <button className="primary" onClick={() => setEditor({ mode: "create" })}>
            New pipeline
          </button>
        )}
      </div>

      {editor.mode !== "closed" && (
        <PipelineEditor
          pipeline={editor.mode === "edit" ? editor.pipeline : undefined}
          onSaved={() => {
            setEditor({ mode: "closed" });
            reload();
          }}
          onCancel={() => setEditor({ mode: "closed" })}
        />
      )}

      {pipelines === null ? (
        <p className="muted">Loading…</p>
      ) : pipelines.length === 0 ? (
        <div className="empty">No pipelines yet. Create one to get started.</div>
      ) : (
        <table className="data">
          <thead>
            <tr>
              <th>Name</th>
              <th>Version</th>
              <th>Status</th>
              <th>Default</th>
              <th style={{ width: 260 }}></th>
            </tr>
          </thead>
          <tbody>
            {pipelines.map((p) => (
              <tr key={p.id} style={{ opacity: p.enabled ? 1 : 0.55 }}>
                <td>
                  <strong>{p.display_name}</strong>
                  <div className="muted" style={{ fontSize: 12 }}>
                    <code>{p.name}</code>
                  </div>
                </td>
                <td>v{p.version}</td>
                <td>
                  {p.enabled ? (
                    <span className="badge" data-status="approved">
                      Enabled
                    </span>
                  ) : (
                    <span className="badge" data-status="draft">
                      Disabled
                    </span>
                  )}
                </td>
                <td>
                  {p.is_default ? (
                    <span className="badge" data-status="submitted">
                      Default
                    </span>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button onClick={() => openEdit(p.id)}>Edit</button>
                    {!p.is_default && p.enabled && (
                      <button
                        onClick={() =>
                          guarded(async () => {
                            await setDefaultPipeline(p.id);
                          })
                        }
                      >
                        Set default
                      </button>
                    )}
                    <button
                      onClick={() =>
                        guarded(async () => {
                          await updatePipeline(p.id, { enabled: !p.enabled });
                        })
                      }
                    >
                      {p.enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      className="danger-btn"
                      onClick={() =>
                        guarded(async () => {
                          if (
                            !window.confirm(
                              `Delete pipeline "${p.display_name}"? Past runs keep their snapshot and are unaffected.`,
                            )
                          )
                            return;
                          await deletePipeline(p.id);
                        })
                      }
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
