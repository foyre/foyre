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
