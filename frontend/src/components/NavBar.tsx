import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { UserMenu } from "./UserMenu";

export function NavBar() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  return (
    <nav className="nav">
      <NavLink to="/requests" className="brand" aria-label="Foyre home">
        <img
          src="/foyre-logo.png"
          alt=""
          className="brand-logo"
          aria-hidden="true"
        />
        <span className="brand-text">Foyre</span>
      </NavLink>
      <div className="nav-links">
        <NavLink
          to="/requests"
          className={({ isActive }) =>
            isActive ? "nav-link is-active" : "nav-link"
          }
        >
          Requests
        </NavLink>
        {isAdmin && (
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              isActive ? "nav-link is-active" : "nav-link"
            }
          >
            Administration
          </NavLink>
        )}
      </div>
      <span className="spacer" />
      <UserMenu />
    </nav>
  );
}
