// Mirrors backend enums in app/domain/enums.py.
export const PRIVILEGED_ROLES = [
    "reviewer",
    "architect",
    "admin",
];
export function isPrivileged(role) {
    return PRIVILEGED_ROLES.includes(role);
}
