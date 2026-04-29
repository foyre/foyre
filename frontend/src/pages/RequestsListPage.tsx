import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiErrorMessage } from "../api/errors";
import { listRequests } from "../api/requests";
import { useAuth } from "../auth/useAuth";
import { RiskBadge } from "../components/RiskBadge";
import { StatusBadge } from "../components/StatusBadge";
import {
  type IntakeRequest,
  type RequestStatus,
  isPrivileged,
} from "../types/domain";

function appName(r: IntakeRequest): string {
  const v = (r.payload as { application_name?: string }).application_name;
  return v && v.trim() ? v : "(untitled)";
}

type Filter = "all" | RequestStatus;

const FILTER_ORDER: readonly Filter[] = [
  "all",
  "draft",
  "submitted",
  "ready_for_review",
  "under_review",
  "approved",
  "rejected",
];

const FILTER_LABELS: Record<Filter, string> = {
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
] as const;

function matchesSearch(r: IntakeRequest, rawQuery: string): boolean {
  const needle = rawQuery.toLowerCase().replace(/^#/, "").trim();
  if (!needle) return true;

  // Exact ID match short-circuits (e.g. "42" or "#42").
  if (needle === String(r.id)) return true;

  const haystack: string[] = [
    appName(r),
    r.created_by?.username ?? "",
    r.status.replace(/_/g, " "),
  ];
  const p = r.payload as Record<string, unknown>;
  for (const key of SEARCHABLE_PAYLOAD_FIELDS) {
    const v = p[key];
    if (typeof v === "string" && v) haystack.push(v);
  }

  return haystack.some((s) => s.toLowerCase().includes(needle));
}

export function RequestsListPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<IntakeRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");

  const showOwner = user ? isPrivileged(user.role) : false;

  useEffect(() => {
    listRequests()
      .then(setItems)
      .catch((e) => setError(apiErrorMessage(e)));
  }, []);

  // 1) Apply search first.
  const afterSearch = useMemo(() => {
    if (!items) return [];
    if (!query.trim()) return items;
    return items.filter((r) => matchesSearch(r, query));
  }, [items, query]);

  // 2) Compute filter-pill counts on the search-filtered set so the pills
  //    always reflect what's currently visible given the active search.
  const counts = useMemo(() => {
    const out: Record<Filter, number> = {
      all: 0,
      draft: 0,
      submitted: 0,
      ready_for_review: 0,
      under_review: 0,
      approved: 0,
      rejected: 0,
    };
    out.all = afterSearch.length;
    for (const r of afterSearch) out[r.status] += 1;
    return out;
  }, [afterSearch]);

  // 3) Apply status filter to produce the final visible list.
  const visible = useMemo(() => {
    if (filter === "all") return afterSearch;
    return afterSearch.filter((r) => r.status === filter);
  }, [afterSearch, filter]);

  const hasQuery = query.trim().length > 0;
  const total = items?.length ?? 0;

  return (
    <section>
      <div className="header-row">
        <h2>Requests</h2>
        <Link to="/requests/new">
          <button className="primary">New request</button>
        </Link>
      </div>

      {error && <div className="error">{error}</div>}

      {items === null && !error && <p className="muted">Loading…</p>}

      {items && items.length > 0 && (
        <>
          <div className="search-bar">
            <input
              type="search"
              className="search-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by ID, application, requester, team, description…"
              aria-label="Search requests"
            />
            {hasQuery && (
              <span className="search-summary">
                Showing {visible.length} of {total}
                {filter !== "all" && (
                  <>
                    {" "}
                    (filter: <strong>{FILTER_LABELS[filter]}</strong>)
                  </>
                )}
              </span>
            )}
          </div>

          <div
            className="filter-bar"
            role="toolbar"
            aria-label="Filter by status"
          >
            {FILTER_ORDER.map((f) => {
              const count = counts[f];
              // Hide zero-count filters except "all" so the bar stays clean.
              if (f !== "all" && count === 0) return null;
              const selected = filter === f;
              return (
                <button
                  key={f}
                  type="button"
                  className={`filter-pill${selected ? " is-selected" : ""}`}
                  aria-pressed={selected}
                  onClick={() => setFilter(f)}
                >
                  {FILTER_LABELS[f]}
                  <span className="filter-pill-count">{count}</span>
                </button>
              );
            })}
          </div>
        </>
      )}

      {items && items.length === 0 && (
        <div className="empty">
          No requests yet.{" "}
          <Link to="/requests/new">Create the first one</Link>.
        </div>
      )}

      {items && items.length > 0 && visible.length === 0 && (
        <div className="empty">
          {hasQuery ? (
            <>
              No requests match <strong>"{query}"</strong>
              {filter !== "all" && (
                <>
                  {" "}
                  with status <strong>{FILTER_LABELS[filter]}</strong>
                </>
              )}
              .{" "}
              <button
                className="link-like"
                onClick={() => {
                  setQuery("");
                  setFilter("all");
                }}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  color: "var(--accent)",
                  cursor: "pointer",
                  textDecoration: "underline",
                }}
              >
                Clear search
              </button>
            </>
          ) : (
            <>
              No requests with status <strong>{FILTER_LABELS[filter]}</strong>
              .{" "}
              <button
                className="link-like"
                onClick={() => setFilter("all")}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  color: "var(--accent)",
                  cursor: "pointer",
                  textDecoration: "underline",
                }}
              >
                Show all
              </button>
            </>
          )}
        </div>
      )}

      {visible.length > 0 && (
        <table className="data">
          <thead>
            <tr>
              <th style={{ width: 64 }}>ID</th>
              <th>Application</th>
              {showOwner && <th>Requester</th>}
              <th>Status</th>
              <th>Risk</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.id}>
                <td>
                  <Link to={`/requests/${r.id}`}>#{r.id}</Link>
                </td>
                <td>
                  <Link to={`/requests/${r.id}`}>{appName(r)}</Link>
                </td>
                {showOwner && (
                  <td>
                    {r.created_by?.username ?? `#${r.created_by_id}`}
                    {r.created_by && (
                      <span className="muted"> · {r.created_by.role}</span>
                    )}
                  </td>
                )}
                <td>
                  <StatusBadge status={r.status} />
                </td>
                <td>
                  <RiskBadge level={r.risk_level} />
                </td>
                <td className="muted">
                  {new Date(r.updated_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
