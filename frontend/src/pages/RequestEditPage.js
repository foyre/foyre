import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getRequest, submitRequest, updateRequest } from "../api/requests";
import { IntakeForm } from "../features/intakeForm/IntakeForm";
export function RequestEditPage() {
    const { id } = useParams();
    const reqId = Number(id);
    const navigate = useNavigate();
    const [req, setReq] = useState(null);
    useEffect(() => {
        getRequest(reqId).then(setReq);
    }, [reqId]);
    if (!req)
        return _jsx("p", { children: "Loading\u2026" });
    const onSave = async (payload) => {
        await updateRequest(reqId, payload);
        navigate(`/requests/${reqId}`);
    };
    const onSubmit = async (payload) => {
        await updateRequest(reqId, payload);
        await submitRequest(reqId);
        navigate(`/requests/${reqId}`);
    };
    return (_jsxs("section", { children: [_jsxs("h2", { children: ["Edit draft #", reqId] }), _jsx(IntakeForm, { initialValues: req.payload, onSaveDraft: onSave, onSubmit: onSubmit })] }));
}
