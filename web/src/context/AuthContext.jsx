import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { api } from '../api';

const AuthContext = createContext(null);
const TOKEN = 'super_agent_token';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem(TOKEN)) {
      setLoading(false);
      return;
    }
    api.me()
      .then(setUser)
      .catch(() => localStorage.removeItem(TOKEN))
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo(() => ({
    user,
    loading,
    login: async (username, password, role, remember = true) => {
      const data = await api.login(username, password, role);
      if (!data.user || data.user.role !== role) {
        throw new Error('The selected role does not match this account.');
      }
      localStorage.setItem(TOKEN, data.token);
      if (!remember) sessionStorage.setItem('super_agent_session', '1');
      setUser(data.user);
      return data.user;
    },
    logout: () => {
      localStorage.removeItem(TOKEN);
      sessionStorage.removeItem('super_agent_session');
      setUser(null);
    },
  }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
