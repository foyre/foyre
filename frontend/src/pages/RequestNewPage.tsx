import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createRequest,
  submitRequest,
  updateRequest,
} from "../api/requests";
import { IntakeForm } from "../features/intakeForm/IntakeForm";

export function RequestNewPage() {
  const navigate = useNavigate();
  // If a save-then-submit flow is interrupted by an error, reuse the created
  // draft id on retry instead of creating a duplicate.
  const [draftId, setDraftId] = useState<number | null>(null);

  const ensureDraft = async (payload: Record<string, unknown>): Promise<number> => {
    if (draftId !== null) {
      await updateRequest(draftId, payload);
      return draftId;
    }
    const created = await createRequest(payload);
    setDraftId(created.id);
    return created.id;
  };

  const onSave = async (payload: Record<string, unknown>) => {
    const id = await ensureDraft(payload);
    navigate(`/requests/${id}`);
  };

  const onSubmit = async (payload: Record<string, unknown>) => {
    const id = await ensureDraft(payload);
    await submitRequest(id);
    navigate(`/requests/${id}`);
  };

  return (
    <section>
      <h2>New request</h2>
      <IntakeForm onSaveDraft={onSave} onSubmit={onSubmit} />
    </section>
  );
}
