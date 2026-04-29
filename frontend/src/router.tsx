import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/useAuth";
import { Layout } from "./components/Layout";
import { AccountPage } from "./pages/AccountPage";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { AdminUsersPage } from "./pages/admin/AdminUsersPage";
import { AdminValidationEnvironmentsPage } from "./pages/admin/AdminValidationEnvironmentsPage";
import { ForcePasswordChangePage } from "./pages/ForcePasswordChangePage";
import { LoginPage } from "./pages/LoginPage";
import { RequestDetailPage } from "./pages/RequestDetailPage";
import { RequestEditPage } from "./pages/RequestEditPage";
import { RequestNewPage } from "./pages/RequestNewPage";
import { RequestsListPage } from "./pages/RequestsListPage";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="page muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.must_change_password && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/requests" replace />;
  return <>{children}</>;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/change-password"
        element={
          <RequireAuth>
            <ForcePasswordChangePage />
          </RequireAuth>
        }
      />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Navigate to="/requests" replace />} />
        <Route path="/requests" element={<RequestsListPage />} />
        <Route path="/requests/new" element={<RequestNewPage />} />
        <Route path="/requests/:id" element={<RequestDetailPage />} />
        <Route path="/requests/:id/edit" element={<RequestEditPage />} />

        <Route path="/account" element={<AccountPage />} />

        {/* Legacy /settings redirects to /account so any existing bookmarks
            don't 404. Admin stuff moved to /admin/*. */}
        <Route path="/settings" element={<Navigate to="/account" replace />} />

        <Route
          path="/admin"
          element={
            <RequireAdmin>
              <AdminLayout />
            </RequireAdmin>
          }
        >
          <Route index element={<Navigate to="users" replace />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route
            path="validation-environments"
            element={<AdminValidationEnvironmentsPage />}
          />
        </Route>
      </Route>
    </Routes>
  );
}
