import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { listComments } from "../../api/requests";
export function CommentList({ requestId, reloadKey = 0, }) {
    const [items, setItems] = useState(null);
    useEffect(() => {
        listComments(requestId).then(setItems);
    }, [requestId, reloadKey]);
    if (items === null)
        return _jsx("p", { className: "muted", children: "Loading\u2026" });
    if (items.length === 0)
        return _jsx("p", { className: "muted", children: "No comments yet." });
    return (_jsx("ul", { className: "comments-list", children: items.map((c) => (_jsxs("li", { children: [_jsxs("div", { className: "meta-row", children: [_jsx("strong", { children: c.author?.username ?? `user #${c.author_id}` }), c.author && _jsxs("span", { className: "muted", children: [" \u00B7 ", c.author.role] }), _jsxs("span", { className: "muted", children: [" \u00B7 ", new Date(c.created_at).toLocaleString()] })] }), _jsx("div", { children: c.body })] }, c.id))) }));
}
