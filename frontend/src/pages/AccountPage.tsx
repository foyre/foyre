import { useState } from "react";
import { useAuth } from "../auth/useAuth";
import { PasswordForm } from "../features/settings/PasswordForm";
import { ROLE_DESCRIPTIONS } from "../features/settings/roleDescriptions";

/**
 * Personal account page. Anything account-specific lives here: profile info,
 * password change, and (eventually) personal preferences. System-wide / admin
 * settings live under /admin.
 */
export function AccountPage() {
  const { user } = useAuth();
  const [showPasswordForm, setShowPasswordForm] = useState(false);

  if (!user) return null;

  return (
    <section>
      <div className="header-row">
        <h2>Your account</h2>
      </div>

      <div className="card">
        <dl className="meta" style={{ marginBottom: 0 }}>
          <dt>Username</dt>
          <dd>{user.username}</dd>
          <dt>Email</dt>
          <dd>{user.email}</dd>
          <dt>Role</dt>
          <dd
            title={ROLE_DESCRIPTIONS[user.role].short}
            style={{ cursor: "help" }}
          >
            {ROLE_DESCRIPTIONS[user.role].label}{" "}
            <span className="muted" style={{ fontSize: 12 }}>
              — {ROLE_DESCRIPTIONS[user.role].short}
            </span>
          </dd>
          <dt>Password</dt>
          <dd>
            {!showPasswordForm ? (
              <button onClick={() => setShowPasswordForm(true)}>
                Change password
              </button>
            ) : (
              <div style={{ marginTop: 4 }}>
                <PasswordForm
                  onSuccess={() => setShowPasswordForm(false)}
                  secondaryAction={
                    <button
                      type="button"
                      onClick={() => setShowPasswordForm(false)}
                    >
                      Cancel
                    </button>
                  }
                />
              </div>
            )}
          </dd>
        </dl>
      </div>
    </section>
  );
}
