import { NavLink, Outlet } from "react-router-dom";

/**
 * Admin area shell. Horizontal tabs at the top; the active tab renders via
 * <Outlet /> in the panel below. Add future admin surfaces (auth providers,
 * policy rules, etc.) as new tabs here.
 */
export function AdminLayout() {
  return (
    <section>
      <div className="header-row">
        <h2>Administration</h2>
      </div>

      <div className="admin-tabs" role="tablist" aria-label="Administration sections">
        <NavLink
          to="/admin/users"
          role="tab"
          className={({ isActive }) =>
            isActive ? "admin-tab is-active" : "admin-tab"
          }
        >
          Users
        </NavLink>
        <NavLink
          to="/admin/validation-environments"
          role="tab"
          className={({ isActive }) =>
            isActive ? "admin-tab is-active" : "admin-tab"
          }
        >
          Validation environments
        </NavLink>
      </div>

      <div className="admin-panel">
        <Outlet />
      </div>
    </section>
  );
}
