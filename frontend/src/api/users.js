import { request } from "./client";
export function changeMyPassword(currentPassword, newPassword) {
    return request("/users/me/password", {
        method: "POST",
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
        }),
    });
}
export function listUsers() {
    return request("/admin/users");
}
export function createUser(input) {
    return request("/admin/users", {
        method: "POST",
        body: JSON.stringify(input),
    });
}
export function updateUser(id, patch) {
    return request(`/admin/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
    });
}
