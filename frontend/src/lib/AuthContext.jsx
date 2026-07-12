import { useCallback, useEffect, useState } from "react";
import { getMe, login as apiLogin } from "../api";
import { AuthContext } from "./auth-context";

const STORAGE_KEY = "super_agent_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState(null);
  const [restoring, setRestoring] = useState(true);

  // Restore a session from a stored token on page load (e.g. a refresh)
  // instead of forcing a re-login every time.
  useEffect(() => {
    if (!token) {
      setRestoring(false);
      return;
    }
    let cancelled = false;
    getMe(token)
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        if (!cancelled) {
          localStorage.removeItem(STORAGE_KEY);
          setToken(null);
        }
      })
      .finally(() => {
        if (!cancelled) setRestoring(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const login = useCallback(async (username, password, role) => {
    const { token: newToken, user: loggedInUser } = await apiLogin(username, password, role);
    localStorage.setItem(STORAGE_KEY, newToken);
    setToken(newToken);
    setUser(loggedInUser);
    return loggedInUser;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, restoring, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
