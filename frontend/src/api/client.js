const TOKEN_KEY = "foyre_token";
export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
    if (token)
        localStorage.setItem(TOKEN_KEY, token);
    else
        localStorage.removeItem(TOKEN_KEY);
}
/**
 * Structured error for non-2xx responses. `detail` holds the parsed JSON body
 * when available, otherwise the raw text. Forms use this to surface field-level
 * validation errors returned by the backend (422).
 */
export class ApiError extends Error {
    status;
    detail;
    constructor(status, detail) {
        super(`${status}`);
        this.status = status;
        this.detail = detail;
        this.name = "ApiError";
    }
}
export async function request(path, init = {}) {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    const token = getToken();
    if (token)
        headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(`/api${path}`, { ...init, headers });
    if (!res.ok) {
        let detail;
        try {
            detail = await res.clone().json();
        }
        catch {
            detail = await res.text();
        }
        throw new ApiError(res.status, detail);
    }
    if (res.status === 204)
        return undefined;
    return (await res.json());
}
