import { useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { addComment } from "../../api/requests";

export function CommentComposer({
  requestId,
  onPosted,
}: {
  requestId: number;
  onPosted?: () => void;
}) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const trimmed = body.trim();
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    try {
      await addComment(requestId, trimmed);
      setBody("");
      onPosted?.();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ marginTop: 12 }}>
      {error && <div className="error">{error}</div>}
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={3}
        placeholder="Add a comment…"
      />
      <div className="form-actions">
        <button
          className="primary"
          onClick={submit}
          disabled={busy || body.trim().length === 0}
        >
          {busy ? "Posting…" : "Post comment"}
        </button>
      </div>
    </div>
  );
}
