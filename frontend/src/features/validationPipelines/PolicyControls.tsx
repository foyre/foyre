import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import {
  getValidationPolicy,
  updateValidationPolicy,
} from "../../api/validationPolicy";
import type { ValidationPolicy } from "../../types/domain";

type ToggleKey = keyof Pick<
  ValidationPolicy,
  | "require_validation_before_approval"
  | "block_approval_on_failed_validation"
  | "allow_validation_override"
>;

const TOGGLES: { key: ToggleKey; label: string; help: string }[] = [
  {
    key: "require_validation_before_approval",
    label: "Require a completed validation run before approval",
    help: "Blocks approval until at least one validation pipeline run has completed.",
  },
  {
    key: "block_approval_on_failed_validation",
    label: "Block approval when the latest run has blocking failures",
    help: "When on, a blocking failure must be resolved or overridden before approval.",
  },
  {
    key: "allow_validation_override",
    label: "Allow reviewers to override a blocked approval (with a reason)",
    help: "When off, a blocked approval cannot be overridden by anyone.",
  },
];

export function PolicyControls() {
  const [policy, setPolicy] = useState<ValidationPolicy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<ToggleKey | null>(null);

  useEffect(() => {
    getValidationPolicy()
      .then(setPolicy)
      .catch((e) => setError(apiErrorMessage(e)));
  }, []);

  const toggle = async (key: ToggleKey) => {
    if (!policy) return;
    setBusyKey(key);
    setError(null);
    setFlash(null);
    try {
      const updated = await updateValidationPolicy({ [key]: !policy[key] });
      setPolicy(updated);
      setFlash("Policy updated.");
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <h4 style={{ marginTop: 0, marginBottom: 4 }}>Approval policy</h4>
      <p className="muted" style={{ marginTop: 0, marginBottom: 12, fontSize: 13 }}>
        Controls how validation results gate the approval decision.
      </p>
      {error && <div className="error">{error}</div>}
      {flash && (
        <div className="muted" style={{ marginBottom: 8 }}>
          {flash}
        </div>
      )}
      {policy === null ? (
        <p className="muted">Loading…</p>
      ) : (
        <div className="stack">
          {TOGGLES.map((t) => (
            <label
              key={t.key}
              className="inline-toggle"
              style={{ alignItems: "flex-start", gap: 10 }}
            >
              <input
                type="checkbox"
                checked={policy[t.key]}
                disabled={busyKey !== null}
                onChange={() => toggle(t.key)}
                style={{ marginTop: 3 }}
              />
              <span>
                {t.label}
                <span
                  className="muted"
                  style={{ display: "block", fontSize: 12, fontWeight: 400 }}
                >
                  {t.help}
                </span>
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
