import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { createUser, listUsers, updateUser } from "../../api/users";
import { useAuth } from "../../auth/useAuth";
import type { Role, User } from "../../types/domain";
import { generateTempPassword } from "./generateTempPassword";
import { NewUserCallout, type NewUserInfo } from "./NewUserCallout";
import { RoleLegend } from "./RoleLegend";
import {
  ALL_ROLES_TOOLTIP,
  ROLE_DESCRIPTIONS,
  ROLE_ORDER,
} from "./roleDescriptions";

export function UserManagement() {
  const { user: current } = useAuth();
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newUser, setNewUser] = useState<NewUserInfo | null>(null);

  const reload = async () => {
    try {
      setUsers(await listUsers());
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

  const confirmDeactivate = (u: User, targetActive: boolean) => {
    if (!targetActive) {
      return window.confirm(
        `Deactivate "${u.username}"?\n\n` +
          `They will no longer be able to log in. Their past requests, ` +
          `comments, and history entries are preserved. You can reactivate ` +
          `them at any time.`,
      );
    }
    return true;
  };

  return (
    <div>
      {error && <div className="error">{error}</div>}
      {flash && (
        <div className="muted" style={{ marginBottom: 12 }}>
          {flash}
        </div>
      )}

      {newUser && (
        <NewUserCallout info={newUser} onDismiss={() => setNewUser(null)} />
      )}

      <div className="form-actions" style={{ marginBottom: 12 }}>
        {!showCreate && (
          <button className="primary" onClick={() => setShowCreate(true)}>
            Create user
          </button>
        )}
      </div>

      {showCreate && (
        <CreateUserForm
          onCreated={(info) => {
            setShowCreate(false);
            setNewUser(info);
            guarded(reload);
          }}
          onCancel={() => setShowCreate(false)}
        />
      )}

      <h4 style={{ marginTop: 24, marginBottom: 4 }}>Existing users</h4>
      <p className="muted" style={{ marginTop: 0, marginBottom: 12 }}>
        Users aren't hard-deleted — they're <strong>deactivated</strong> so
        their history stays intact. Deactivated users can't log in; you can
        reactivate anytime.
      </p>
      <RoleLegend />
      {users === null ? (
        <p className="muted">Loading…</p>
      ) : (
        <table className="data">
          <thead>
            <tr>
              <th style={{ width: 64 }}>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th title={ALL_ROLES_TOOLTIP} style={{ cursor: "help" }}>
                Role <span aria-hidden>&#9432;</span>
              </th>
              <th>Status</th>
              <th>Created</th>
              <th style={{ width: 140 }}></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const isSelf = current?.id === u.id;
              return (
                <tr key={u.id} style={{ opacity: u.is_active ? 1 : 0.55 }}>
                  <td>#{u.id}</td>
                  <td>
                    {u.username}
                    {isSelf && <span className="muted"> (you)</span>}
                    {u.must_change_password && (
                      <span
                        className="muted"
                        title="This user has a temporary password and must change it on next login."
                        style={{ marginLeft: 6 }}
                      >
                        · temp pw
                      </span>
                    )}
                  </td>
                  <td className="muted">{u.email}</td>
                  <td>
                    <select
                      value={u.role}
                      disabled={isSelf}
                      onChange={(e) =>
                        guarded(async () => {
                          await updateUser(u.id, {
                            role: e.target.value as Role,
                          });
                          await reload();
                        })
                      }
                      title={
                        isSelf
                          ? "Admins can't change their own role"
                          : ROLE_DESCRIPTIONS[u.role].short
                      }
                    >
                      {ROLE_ORDER.map((r) => (
                        <option
                          key={r}
                          value={r}
                          title={ROLE_DESCRIPTIONS[r].short}
                        >
                          {ROLE_DESCRIPTIONS[r].label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    {u.is_active ? (
                      <span className="badge" data-status="approved">
                        Active
                      </span>
                    ) : (
                      <span className="badge" data-status="rejected">
                        Deactivated
                      </span>
                    )}
                  </td>
                  <td className="muted">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    {isSelf ? (
                      <span className="muted" style={{ fontSize: 12 }}>
                        —
                      </span>
                    ) : u.is_active ? (
                      <button
                        onClick={() =>
                          guarded(async () => {
                            if (!confirmDeactivate(u, false)) return;
                            await updateUser(u.id, { is_active: false });
                            await reload();
                          }, `${u.username} deactivated.`)
                        }
                      >
                        Deactivate
                      </button>
                    ) : (
                      <button
                        onClick={() =>
                          guarded(async () => {
                            await updateUser(u.id, { is_active: true });
                            await reload();
                          }, `${u.username} reactivated.`)
                        }
                      >
                        Reactivate
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

function CreateUserForm({
  onCreated,
  onCancel,
}: {
  onCreated: (info: NewUserInfo) => void;
  onCancel: () => void;
}) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  // Prefill with a strong generated temp password. Admin can regenerate or
  // type their own. The field stays `type="text"` so they can see / copy it.
  const [password, setPassword] = useState(() => generateTempPassword());
  const [role, setRole] = useState<Role>("requester");
  const [mustChange, setMustChange] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await createUser({
        username,
        email,
        password,
        role,
        must_change_password: mustChange,
      });
      // Bubble up BEFORE resetting so the callout can render the password.
      onCreated({
        username,
        tempPassword: password,
        mustChangeOnLogin: mustChange,
      });
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <h4 style={{ marginTop: 0, marginBottom: 4 }}>Create user</h4>
      <p className="muted" style={{ marginTop: 0, marginBottom: 12 }}>
        A strong temporary password has been generated below. You'll see it
        again after creating the user so you can share it out-of-band. If the
        box is checked, the user must change it on first login.
      </p>
      {error && <div className="error">{error}</div>}
      <form
        onSubmit={onSubmit}
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 12,
        }}
      >
        <label className="field" style={{ margin: 0 }}>
          <span className="label">Username</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="off"
          />
        </label>
        <label className="field" style={{ margin: 0 }}>
          <span className="label">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="off"
          />
        </label>
        <label className="field" style={{ margin: 0 }}>
          <span className="label">Temporary password</span>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              type="text"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="off"
              style={{
                fontFamily:
                  "ui-monospace, SFMono-Regular, Menlo, monospace",
              }}
            />
            <button
              type="button"
              onClick={() => setPassword(generateTempPassword())}
              title="Generate a new random password"
            >
              Regenerate
            </button>
          </div>
        </label>
        <label className="field" style={{ margin: 0 }}>
          <span
            className="label"
            title={ALL_ROLES_TOOLTIP}
            style={{ cursor: "help" }}
          >
            Role{" "}
            <span
              aria-hidden
              style={{ color: "var(--muted)", fontWeight: 400 }}
            >
              &#9432;
            </span>
          </span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
            title={ROLE_DESCRIPTIONS[role].short}
          >
            {ROLE_ORDER.map((r) => (
              <option
                key={r}
                value={r}
                title={ROLE_DESCRIPTIONS[r].short}
              >
                {ROLE_DESCRIPTIONS[r].label}
              </option>
            ))}
          </select>
          <span
            className="muted"
            style={{ fontSize: 12, marginTop: 4, display: "block" }}
          >
            {ROLE_DESCRIPTIONS[role].short}
          </span>
        </label>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            gridColumn: "1 / -1",
          }}
        >
          <input
            type="checkbox"
            checked={mustChange}
            onChange={(e) => setMustChange(e.target.checked)}
            style={{ width: "auto" }}
          />
          <span>Require user to change this password on first login</span>
        </label>
        <div
          className="form-actions"
          style={{ gridColumn: "1 / -1", marginTop: 0 }}
        >
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Creating…" : "Create user"}
          </button>
          <button type="button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
