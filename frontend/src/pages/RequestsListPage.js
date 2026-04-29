import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiErrorMessage } from "../api/errors";
import { listRequests } from "../api/requests";
import { useAuth } from "../auth/useAuth";
import { RiskBadge } from "../components/RiskBadge";
import { StatusBadge } from "../components/StatusBadge";
import { isPrivileged, } from "../types/domain";
function appName(r) {
    const v = r.payload.application_name;
    return v && v.trim() ? v : "(untitled)";
}
const FILTER_ORDER = [
    "all",
    "draft",
    "submitted",
    "ready_for_review",
    "under_review",
    "approved",
    "rejected",
];
const FILTER_LABELS = {
    all: "All",
    draft: "Draft",
    submitted: "Submitted",
    ready_for_review: "Ready for review",
    under_review: "Under review",
    approved: "Approved",
    rejected: "Rejected",
};
// Payload fields worth searching over. If you add new form fields that are
// useful to locate by, append them here.
const SEARCHABLE_PAYLOAD_FIELDS = [
    "application_name",
    "business_owner",
    "technical_owner",
    "team",
    "description",
    "vector_db_name",
    "justification",
    "timeline",
];
function matchesSearch(r, rawQuery) {
    const needle = rawQuery.toLowerCase().replace(/^#/, "").trim();
    if (!needle)
        return true;
    // Exact ID match short-circuits (e.g. "42" or "#42").
    if (needle === String(r.id))
        return true;
    const haystack = [
        appName(r),
        r.created_by?.username ?? "",
        r.status.replace(/_/g, " "),
    ];
    const p = r.payload;
    for (const key of SEARCHABLE_PAYLOAD_FIELDS) {
        const v = p[key];
        if (typeof v === "string" && v)
            haystack.push(v);
    }
    return haystack.some((s) => s.toLowerCase().includes(needle));
}
export function RequestsListPage() {
    const { user } = useAuth();
    const [items, setItems] = useState(null);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState("all");
    const [query, setQuery] = useState("");
    const showOwner = user ? isPrivileged(user.role) : false;
    useEffect(() => {
        listRequests()
            .then(setItems)
            .catch((e) => setError(apiErrorMessage(e)));
    }, []);
    // 1) Apply search first.
    const afterSearch = useMemo(() => {
        if (!items)
            return [];
        if (!query.trim())
            return items;
        return items.filter((r) => matchesSearch(r, query));
    }, [items, query]);
    // 2) Compute filter-pill counts on the search-filtered set so the pills
    //    always reflect what's currently visible given the active search.
    const counts = useMemo(() => {
        const out = {
            all: 0,
            draft: 0,
            submitted: 0,
            ready_for_review: 0,
            under_review: 0,
            approved: 0,
            rejected: 0,
        };
        out.all = afterSearch.length;
        for (const r of afterSearch)
            out[r.status] += 1;
        return out;
    }, [afterSearch]);
    // 3) Apply status filter to produce the final visible list.
    const visible = useMemo(() => {
        if (filter === "all")
            return afterSearch;
        return afterSearch.filter((r) => r.status === filter);
    }, [afterSearch, filter]);
    const hasQuery = query.trim().length > 0;
    const total = items?.length ?? 0;
    return (_jsxs("section", { children: [_jsxs("div", { className: "header-row", children: [_jsx("h2", { children: "Requests" }), _jsx(Link, { to: "/requests/new", children: _jsx("button", { className: "primary", children: "New request" }) })] }), error && _jsx("div", { className: "error", children: error }), items === null && !error && _jsx("p", { className: "muted", children: "Loading\u2026" }), items && items.length > 0 && (_jsxs(_Fragment, { children: [_jsxs("div", { className: "search-bar", children: [_jsx("input", { type: "search", className: "search-input", value: query, onChange: (e) => setQuery(e.target.value), placeholder: "Search by ID, application, requester, team, description\u2026", "aria-label": "Search requests" }), hasQuery && (_jsxs("span", { className: "search-summary", children: ["Showing ", visible.length, " of ", total, filter !== "all" && (_jsxs(_Fragment, { children: [" ", "(filter: ", _jsx("strong", { children: FILTER_LABELS[filter] }), ")"] }))] }))] }), _jsx("div", { className: "filter-bar", role: "toolbar", "aria-label": "Filter by status", children: FILTER_ORDER.map((f) => {
                            const count = counts[f];
                            // Hide zero-count filters except "all" so the bar stays clean.
                            if (f !== "all" && count === 0)
                                return null;
                            const selected = filter === f;
                            return (_jsxs("button", { type: "button", className: `filter-pill${selected ? " is-selected" : ""}`, "aria-pressed": selected, onClick: () => setFilter(f), children: [FILTER_LABELS[f], _jsx("span", { className: "filter-pill-count", children: count })] }, f));
                        }) })] })), items && items.length === 0 && (_jsxs("div", { className: "empty", children: ["No requests yet.", " ", _jsx(Link, { to: "/requests/new", children: "Create the first one" }), "."] })), items && items.length > 0 && visible.length === 0 && (_jsx("div", { className: "empty", children: hasQuery ? (_jsxs(_Fragment, { children: ["No requests match ", _jsxs("strong", { children: ["\"", query, "\""] }), filter !== "all" && (_jsxs(_Fragment, { children: [" ", "with status ", _jsx("strong", { children: FILTER_LABELS[filter] })] })), ".", " ", _jsx("button", { className: "link-like", onClick: () => {
                                setQuery("");
                                setFilter("all");
                            }, style: {
                                background: "none",
                                border: "none",
                                padding: 0,
                                color: "var(--accent)",
                                cursor: "pointer",
                                textDecoration: "underline",
                            }, children: "Clear search" })] })) : (_jsxs(_Fragment, { children: ["No requests with status ", _jsx("strong", { children: FILTER_LABELS[filter] }), ".", " ", _jsx("button", { className: "link-like", onClick: () => setFilter("all"), style: {
                                background: "none",
                                border: "none",
                                padding: 0,
                                color: "var(--accent)",
                                cursor: "pointer",
                                textDecoration: "underline",
                            }, children: "Show all" })] })) })), visible.length > 0 && (_jsxs("table", { className: "data", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { style: { width: 64 }, children: "ID" }), _jsx("th", { children: "Application" }), showOwner && _jsx("th", { children: "Requester" }), _jsx("th", { children: "Status" }), _jsx("th", { children: "Risk" }), _jsx("th", { children: "Updated" })] }) }), _jsx("tbody", { children: visible.map((r) => (_jsxs("tr", { children: [_jsx("td", { children: _jsxs(Link, { to: `/requests/${r.id}`, children: ["#", r.id] }) }), _jsx("td", { children: _jsx(Link, { to: `/requests/${r.id}`, children: appName(r) }) }), showOwner && (_jsxs("td", { children: [r.created_by?.username ?? `#${r.created_by_id}`, r.created_by && (_jsxs("span", { className: "muted", children: [" \u00B7 ", r.created_by.role] }))] })), _jsx("td", { children: _jsx(StatusBadge, { status: r.status }) }), _jsx("td", { children: _jsx(RiskBadge, { level: r.risk_level }) }), _jsx("td", { className: "muted", children: new Date(r.updated_at).toLocaleString() })] }, r.id))) })] }))] }));
}
