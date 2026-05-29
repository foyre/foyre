import { useEffect, useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { changeStatus } from "../../api/requests";
import { getApprovalGate } from "../../api/validationRuns";
import type { ApprovalGate, IntakeRequest } from "../../types/domain";

interface Props {
  request: IntakeRequest;
  /** Bumped by the parent when validation state may have changed. */
  reloadKey?: number;
  onApproved: (updated: IntakeRequest) => void;
}

/**
 * Approve button that respects the validation approval gate. If the latest
 * validation run blocks approval, it opens a modal: either an override form
 * (when policy allows) or an explanation that approval can't proceed.
 */
export function ApproveControl({ request: req, reloadKey, onApproved }: Props) {
  const [gate, setGate] = useState<ApprovalGate | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getApprovalGate(req.id)
      .then(setGate)
      .catch(() => setGate(null));
  }, [req.id, reloadKey]);

  const doApprove = async (override?: { reason: string }) => {
    setBusy(true);
    setError(null);
    try {
      const updated = await changeStatus(req.id, "approved", {
        override_validation: override ? true : undefined,
        override_reason: override?.reason,
      });
      setModalOpen(false);
      onApproved(updated);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const onClick = () => {
    setError(null);
    if (gate?.blocked) {
      setModalOpen(true);
    } else {
      void doApprove();
    }
  };

  return (
    <>
      <button className="primary" onClick={onClick} disabled={busy}>
        {gate?.blocked ? "Approve (blocked)" : "Approve"}
      </button>
      {gate && !gate.blocked && gate.impact === "warning" && (
        <span className="muted" style={{ fontSize: 13 }}>
          ⚠ Validation finished with warnings — review before approving.
        </span>
      )}
      {gate && !gate.blocked && gate.missing_validation && (
        <span className="muted" style={{ fontSize: 13 }}>
          No validation run yet — consider running one first.
        </span>
      )}

      {modalOpen && gate && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal">
            <h3 style={{ marginTop: 0 }}>Approval blocked by validation</h3>
            <p>{gate.reason}</p>
            {error && <div className="error">{error}</div>}

            {gate.override_allowed ? (
              <>
                <label className="field">
                  <span className="label">Override reason (required)</span>
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={3}
                    placeholder="e.g. Critical CVE has no fix yet; compensating controls in place. Approved by security lead."
                  />
                </label>
                <div className="form-actions">
                  <button
                    className="primary"
                    disabled={busy || !reason.trim()}
                    onClick={() => doApprove({ reason: reason.trim() })}
                  >
                    {busy ? "Approving…" : "Override and approve"}
                  </button>
                  <button onClick={() => setModalOpen(false)} disabled={busy}>
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="muted">
                  Overriding a blocked approval is disabled by policy. Resolve
                  the blocking findings and re-run validation.
                </p>
                <div className="form-actions">
                  <button onClick={() => setModalOpen(false)}>Close</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
