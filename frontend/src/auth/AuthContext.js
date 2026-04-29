import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useEffect, useState } from "react";
import { login as apiLogin, me as apiMe } from "../api/auth";
import { getToken, setToken } from "../api/client";
export const AuthContext = createContext(undefined);
export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
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
    const login = async (username, password) => {
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
    return (_jsx(AuthContext.Provider, { value: { user, loading, login, logout, refreshUser }, children: children }));
}
