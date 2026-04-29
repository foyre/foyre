import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { PasswordForm } from "../features/settings/PasswordForm";

/**
 * Shown (and required) when `user.must_change_password` is true — e.g. the
 * first time a user logs in with an admin-provided temporary password. Uses a
 * standalone layout so it's visually clear this is a gate, not a normal page.
 */
export function ForcePasswordChangePage() {
  const { user, loading } = useAuth();
  if (loading) return <div className="login-wrap muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  // If the flag already isn't set, there's nothing to do here.
  if (!user.must_change_password) return <Navigate to="/requests" replace />;

  return (
    <div className="login-wrap">
      <h1>Set a new password</h1>
      <p className="muted" style={{ marginBottom: 16 }}>
        You're signed in as <strong>{user.username}</strong>. Please replace
        your temporary password before continuing.
      </p>
      <div className="card">
        <PasswordForm primaryLabel="Set new password" />
      </div>
    </div>
  );
}
