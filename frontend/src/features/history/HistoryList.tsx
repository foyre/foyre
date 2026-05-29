import { useEffect, useState } from "react";
import { getHistory } from "../../api/requests";
import type { HistoryEvent } from "../../types/domain";

const EVENT_LABELS: Record<string, string> = {
  created: "Created",
  updated: "Updated",
  submitted: "Submitted",
  status_changed: "Status changed",
  commented: "Commented",
  risk_evaluated: "Risk evaluated",
  validation_env_requested: "Validation environment requested",
  validation_env_ready: "Validation environment ready",
  validation_env_failed: "Validation environment failed",
  validation_env_torn_down: "Validation environment torn down",
  validation_run_started: "Validation run started",
  validation_run_completed: "Validation run completed",
  validation_run_failed: "Validation run failed",
  validation_approval_blocked: "Approval blocked by validation",
  validation_override_used: "Validation override used",
  validation_artifact_created: "Validation artifact created",
};

function describe(e: HistoryEvent): string | null {
  if (!e.detail) return null;
  if (e.event_type === "status_changed") {
    const d = e.detail as { from?: string; to?: string };
    return `${d.from} → ${d.to}`;
  }
  if (e.event_type === "risk_evaluated") {
    const d = e.detail as { level?: string; reasons?: string[] };
    const reasons = d.reasons?.length ? ` (${d.reasons.join("; ")})` : "";
    return `${d.level}${reasons}`;
  }
  if (e.event_type === "validation_run_completed") {
    const d = e.detail as { pipeline?: string; status?: string; approval_impact?: string };
    return `${d.pipeline}: ${d.status} (approval: ${d.approval_impact})`;
  }
  if (e.event_type === "validation_run_started") {
    const d = e.detail as { pipeline?: string };
    return d.pipeline ?? null;
  }
  if (
    e.event_type === "validation_override_used" ||
    e.event_type === "validation_approval_blocked"
  ) {
    const d = e.detail as { reason?: string };
    return d.reason ?? null;
  }
  return null;
}

export function HistoryList({
  requestId,
  reloadKey = 0,
}: {
  requestId: number;
  reloadKey?: number;
}) {
  const [items, setItems] = useState<HistoryEvent[] | null>(null);

  useEffect(() => {
    getHistory(requestId).then(setItems);
  }, [requestId, reloadKey]);

  if (items === null) return <p className="muted">Loading…</p>;
  if (items.length === 0) return <p className="muted">No history yet.</p>;

  return (
    <ul className="history-list">
      {items.map((e) => {
        const desc = describe(e);
        return (
          <li key={e.id}>
            <div className="meta-row">
              <strong>{EVENT_LABELS[e.event_type] ?? e.event_type}</strong>
              <span className="muted">
                {" · "}
                {e.actor?.username ?? `user #${e.actor_id}`}
                {" · "}
                {new Date(e.created_at).toLocaleString()}
              </span>
            </div>
            {desc && <code>{desc}</code>}
          </li>
        );
      })}
    </ul>
  );
}
