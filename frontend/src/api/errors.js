import { ApiError } from "./client";
/**
 * Best-effort human-readable message from any thrown value.
 *
 * - `ApiError` 422: generic "fix the fields" hint (details are already surfaced
 *   next to individual inputs by the form).
 * - Any `ApiError` with a JSON `{detail: "..."}` body: returns that string
 *   (FastAPI's `HTTPException(detail="...")` shape).
 * - Falls back to `err.message` or a generic sentence.
 */
export function apiErrorMessage(err) {
    if (err instanceof ApiError) {
        if (err.status === 422)
            return "Please fix the highlighted fields.";
        const d = err.detail;
        if (typeof d === "string")
            return d;
        if (d && typeof d === "object") {
            const inner = d.detail;
            if (typeof inner === "string")
                return inner;
            if (inner && typeof inner === "object" && typeof inner.message === "string")
                return inner.message;
        }
        return `Request failed (${err.status}).`;
    }
    if (err instanceof Error && err.message)
        return err.message;
    return "Something went wrong.";
}
