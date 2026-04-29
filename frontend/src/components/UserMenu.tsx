import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

/**
 * Dropdown anchored to the current username in the nav.
 *
 * Accessibility:
 *   - Trigger is a real <button> with aria-haspopup="menu", aria-expanded.
 *   - Menu is a <div role="menu"> with role="menuitem" children.
 *   - ESC closes, outside click closes, selecting any item closes.
 */
export function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;

    const onDocClick = (e: MouseEvent) => {
      if (!rootRef.current) return;
      if (e.target instanceof Node && !rootRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!user) return null;

  const go = (path: string) => {
    setOpen(false);
    navigate(path);
  };

  const onSignOut = () => {
    setOpen(false);
    logout();
    navigate("/login", { replace: true });
  };

  const initials = (user.username || "?").slice(0, 2).toUpperCase();

  return (
    <div className="user-menu" ref={rootRef}>
      <button
        type="button"
        className="user-menu-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="user-avatar" aria-hidden="true">{initials}</span>
        <span className="user-menu-name">
          {user.username}
          <span className="user-menu-role">{user.role}</span>
        </span>
        <span className="user-menu-caret" aria-hidden="true">{open ? "\u25B4" : "\u25BE"}</span>
      </button>

      {open && (
        <div className="user-menu-popover" role="menu">
          <div className="user-menu-identity">
            <div className="user-menu-identity-name">{user.username}</div>
            <div className="user-menu-identity-email">{user.email}</div>
            <div className="user-menu-identity-role">
              Signed in as <strong>{user.role}</strong>
            </div>
          </div>
          <div className="user-menu-items">
            <button
              type="button"
              role="menuitem"
              className="user-menu-item"
              onClick={() => go("/account")}
            >
              Your account
            </button>
          </div>
          <div className="user-menu-items user-menu-items-bottom">
            <button
              type="button"
              role="menuitem"
              className="user-menu-item"
              onClick={onSignOut}
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
