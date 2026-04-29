import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (loading) {
    return <div className="login-wrap muted">Loading…</div>;
  }
  if (user) return <Navigate to="/requests" replace />;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(
        err instanceof Error && err.message.startsWith("401")
          ? "Invalid username or password."
          : "Login failed. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <div className="login-brand">
        <img src="/foyre-logo.png" alt="" aria-hidden="true" />
        <h1>Foyre</h1>
      </div>
      <div className="card">
        <form onSubmit={onSubmit}>
          {error && <div className="error">{error}</div>}
          <label className="field">
            <span className="label">Username</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
              required
            />
          </label>
          <label className="field">
            <span className="label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
