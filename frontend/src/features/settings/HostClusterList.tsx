import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import {
  type HostCluster,
  deleteHostCluster,
  listHostClusters,
  testSavedConnection,
} from "../../api/hostClusters";
import { HostClusterForm } from "./HostClusterForm";
import { HostClusterSetupGuide } from "./HostClusterSetupGuide";

type Mode =
  | { kind: "list" }
  | { kind: "create" }
  | { kind: "edit"; row: HostCluster };

export function HostClusterList() {
  const [items, setItems] = useState<HostCluster[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>({ kind: "list" });

  const reload = async () => {
    try {
      setItems(await listHostClusters());
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };
  useEffect(() => {
    reload();
  }, []);

  const guarded = async (fn: () => Promise<void>, successMsg?: string) => {
    setError(null);
    setFlash(null);
    try {
      await fn();
      if (successMsg) setFlash(successMsg);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };

  return (
    <div>
      {error && <div className="error">{error}</div>}
      {flash && (
        <div className="muted" style={{ marginBottom: 12 }}>
          {flash}
        </div>
      )}

      <HostClusterSetupGuide />

      {mode.kind === "list" && (
        <>
          <div className="form-actions" style={{ marginBottom: 12 }}>
            <button className="primary" onClick={() => setMode({ kind: "create" })}>
              Add host cluster
            </button>
          </div>

          {items === null ? (
            <p className="muted">Loading…</p>
          ) : items.length === 0 ? (
            <div className="empty">
              No host clusters configured. Add one to start provisioning
              validation environments.
            </div>
          ) : (
            <table className="data">
              <thead>
                <tr>
                  <th style={{ width: 64 }}>ID</th>
                  <th>Name</th>
                  <th>Provider</th>
                  <th>Connection</th>
                  <th>Default</th>
                  <th>Enabled</th>
                  <th>Last tested</th>
                  <th style={{ width: 220 }}></th>
                </tr>
              </thead>
              <tbody>
                {items.map((h) => (
                  <tr key={h.id} style={{ opacity: h.is_enabled ? 1 : 0.6 }}>
                    <td>#{h.id}</td>
                    <td>
                      <strong>{h.name}</strong>
                      {h.last_test_cluster_version && (
                        <div className="muted" style={{ fontSize: 12 }}>
                          {h.last_test_cluster_version},{" "}
                          {h.last_test_node_count ?? "?"} node
                          {h.last_test_node_count === 1 ? "" : "s"}
                        </div>
                      )}
                    </td>
                    <td>{h.provider}</td>
                    <td>
                      <ConnStatus row={h} />
                    </td>
                    <td>{h.is_default ? "yes" : ""}</td>
                    <td>{h.is_enabled ? "yes" : "no"}</td>
                    <td className="muted" style={{ fontSize: 12 }}>
                      {h.last_tested_at
                        ? new Date(h.last_tested_at).toLocaleString()
                        : "—"}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button
                          onClick={() =>
                            guarded(async () => {
                              await testSavedConnection(h.id);
                              await reload();
                            }, `Tested ${h.name}.`)
                          }
                        >
                          Test
                        </button>
                        <button onClick={() => setMode({ kind: "edit", row: h })}>
                          Edit
                        </button>
                        <button
                          onClick={() =>
                            guarded(async () => {
                              if (
                                !window.confirm(
                                  `Remove host cluster "${h.name}"? ` +
                                    `Any validation environments already provisioned on it will continue running.`,
                                )
                              )
                                return;
                              await deleteHostCluster(h.id);
                              await reload();
                            }, `Removed ${h.name}.`)
                          }
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {mode.kind === "create" && (
        <HostClusterForm
          onSaved={() => {
            setMode({ kind: "list" });
            guarded(reload, "Host cluster added.");
          }}
          onCancel={() => setMode({ kind: "list" })}
        />
      )}

      {mode.kind === "edit" && (
        <HostClusterForm
          initial={mode.row}
          onSaved={() => {
            setMode({ kind: "list" });
            guarded(reload, "Host cluster updated.");
          }}
          onCancel={() => setMode({ kind: "list" })}
        />
      )}
    </div>
  );
}

function ConnStatus({ row }: { row: HostCluster }) {
  switch (row.last_test_status) {
    case "connected":
      return (
        <span
          className="badge"
          data-status="approved"
          title={row.last_test_error ?? ""}
        >
          Connected
        </span>
      );
    case "failed":
      return (
        <span
          className="badge"
          data-status="rejected"
          title={row.last_test_error ?? "connection failed"}
        >
          Failed
        </span>
      );
    default:
      return (
        <span className="badge" data-status="draft">
          Untested
        </span>
      );
  }
}
