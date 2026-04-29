import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getRequest, submitRequest, updateRequest } from "../api/requests";
import { IntakeForm } from "../features/intakeForm/IntakeForm";
import type { IntakeRequest } from "../types/domain";

export function RequestEditPage() {
  const { id } = useParams();
  const reqId = Number(id);
  const navigate = useNavigate();
  const [req, setReq] = useState<IntakeRequest | null>(null);

  useEffect(() => {
    getRequest(reqId).then(setReq);
  }, [reqId]);

  if (!req) return <p>Loading…</p>;

  const onSave = async (payload: Record<string, unknown>) => {
    await updateRequest(reqId, payload);
    navigate(`/requests/${reqId}`);
  };

  const onSubmit = async (payload: Record<string, unknown>) => {
    await updateRequest(reqId, payload);
    await submitRequest(reqId);
    navigate(`/requests/${reqId}`);
  };

  return (
    <section>
      <h2>Edit draft #{reqId}</h2>
      <IntakeForm
        initialValues={req.payload}
        onSaveDraft={onSave}
        onSubmit={onSubmit}
      />
    </section>
  );
}
