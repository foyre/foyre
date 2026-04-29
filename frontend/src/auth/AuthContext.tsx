import { createContext, useEffect, useState, type ReactNode } from "react";
import { login as apiLogin, me as apiMe } from "../api/auth";
import { getToken, setToken } from "../api/client";
import type { User } from "../types/domain";

export interface AuthState {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  /** Re-fetch the current user (e.g. after a password change). */
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    apiMe()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    setToken(res.access_token);
    setUser(res.user);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    setUser(await apiMe());
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}
