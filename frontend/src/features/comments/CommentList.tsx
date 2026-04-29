import { useEffect, useState } from "react";
import { listComments } from "../../api/requests";
import type { Comment } from "../../types/domain";

export function CommentList({
  requestId,
  reloadKey = 0,
}: {
  requestId: number;
  reloadKey?: number;
}) {
  const [items, setItems] = useState<Comment[] | null>(null);

  useEffect(() => {
    listComments(requestId).then(setItems);
  }, [requestId, reloadKey]);

  if (items === null) return <p className="muted">Loading…</p>;
  if (items.length === 0) return <p className="muted">No comments yet.</p>;

  return (
    <ul className="comments-list">
      {items.map((c) => (
        <li key={c.id}>
          <div className="meta-row">
            <strong>{c.author?.username ?? `user #${c.author_id}`}</strong>
            {c.author && <span className="muted"> · {c.author.role}</span>}
            <span className="muted"> · {new Date(c.created_at).toLocaleString()}</span>
          </div>
          <div>{c.body}</div>
        </li>
      ))}
    </ul>
  );
}
