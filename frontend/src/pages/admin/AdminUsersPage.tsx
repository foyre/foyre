import { UserManagement } from "../../features/settings/UserManagement";

export function AdminUsersPage() {
  return (
    <div>
      <p className="muted" style={{ marginTop: 0, marginBottom: 12 }}>
        Create local users, manage roles, and deactivate accounts. You can't
        change your own role or deactivate yourself.
      </p>
      <UserManagement />
    </div>
  );
}
