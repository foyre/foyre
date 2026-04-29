import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createRequest, submitRequest, updateRequest, } from "../api/requests";
import { IntakeForm } from "../features/intakeForm/IntakeForm";
export function RequestNewPage() {
    const navigate = useNavigate();
    // If a save-then-submit flow is interrupted by an error, reuse the created
    // draft id on retry instead of creating a duplicate.
    const [draftId, setDraftId] = useState(null);
    const ensureDraft = async (payload) => {
        if (draftId !== null) {
            await updateRequest(draftId, payload);
            return draftId;
        }
        const created = await createRequest(payload);
        setDraftId(created.id);
        return created.id;
    };
    const onSave = async (payload) => {
        const id = await ensureDraft(payload);
        navigate(`/requests/${id}`);
    };
    const onSubmit = async (payload) => {
        const id = await ensureDraft(payload);
        await submitRequest(id);
        navigate(`/requests/${id}`);
    };
    return (_jsxs("section", { children: [_jsx("h2", { children: "New request" }), _jsx(IntakeForm, { onSaveDraft: onSave, onSubmit: onSubmit })] }));
}
