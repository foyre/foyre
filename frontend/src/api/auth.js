import { request } from "./client";
export function login(username, password) {
    return request("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
    });
}
export function me() {
    return request("/auth/me");
}
