import { useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { changeMyPassword } from "../../api/users";
import { useAuth } from "../../auth/useAuth";

interface Props {
  /** Called after a successful change so the parent can e.g. navigate. */
  onSuccess?: () => void;
  /** Optional trailing button (e.g. Cancel to collapse the panel). */
  secondaryAction?: React.ReactNode;
  primaryLabel?: string;
}

export function PasswordForm({
  onSuccess,
  secondaryAction,
  primaryLabel = "Change password",
}: Props) {
  const { refreshUser } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const reset = () => {
    setCurrent("");
    setNext("");
    setConfirm("");
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setFlash(null);
    if (next.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (next !== confirm) {
      setError("New password and confirmation don't match.");
      return;
    }
    setBusy(true);
    try {
      await changeMyPassword(current, next);
      await refreshUser();
      reset();
      setFlash("Password updated.");
      onSuccess?.();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={onSubmit} style={{ maxWidth: 420 }}>
      {error && <div className="error">{error}</div>}
      <label className="field">
        <span className="label">Current password</span>
        <input
          type="password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      <label className="field">
        <span className="label">New password</span>
        <input
          type="password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          autoComplete="new-password"
          required
          minLength={8}
        />
      </label>
      <label className="field">
        <span className="label">Confirm new password</span>
        <input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoComplete="new-password"
          required
          minLength={8}
        />
      </label>
      <div className="form-actions">
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Updating…" : primaryLabel}
        </button>
        {secondaryAction}
        {flash && <span className="flash">{flash}</span>}
      </div>
    </form>
  );
}
