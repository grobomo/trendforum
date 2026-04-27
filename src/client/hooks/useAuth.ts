import { createContext, useContext, useState, ReactNode, createElement } from 'react';
import { api, setToken, getToken } from '../lib/api';

interface AuthContextType {
  token: string | null;
  login: (password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken());

  const login = async (password: string) => {
    const res = await api.auth.verify(password);
    setToken(res.token);
    setTokenState(res.token);
  };

  const logout = () => {
    setToken(null);
    setTokenState(null);
  };

  return createElement(
    AuthContext.Provider,
    { value: { token, login, logout } },
    children
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
