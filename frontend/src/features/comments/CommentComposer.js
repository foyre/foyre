import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { apiErrorMessage } from "../../api/errors";
import { addComment } from "../../api/requests";
export function CommentComposer({ requestId, onPosted, }) {
    const [body, setBody] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const submit = async () => {
        const trimmed = body.trim();
        if (!trimmed)
            return;
        setBusy(true);
        setError(null);
        try {
            await addComment(requestId, trimmed);
            setBody("");
            onPosted?.();
        }
        catch (err) {
            setError(apiErrorMessage(err));
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs("div", { style: { marginTop: 12 }, children: [error && _jsx("div", { className: "error", children: error }), _jsx("textarea", { value: body, onChange: (e) => setBody(e.target.value), rows: 3, placeholder: "Add a comment\u2026" }), _jsx("div", { className: "form-actions", children: _jsx("button", { className: "primary", onClick: submit, disabled: busy || body.trim().length === 0, children: busy ? "Posting…" : "Post comment" }) })] }));
}
