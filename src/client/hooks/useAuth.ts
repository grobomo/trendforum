import { createContext, useContext, useState, ReactNode, createElement } from 'react';
import { api, setToken, getToken } from '../lib/api';

interface ProfileInfo {
  id: number;
  pseudonym: string;
}

interface AuthContextType {
  token: string | null;
  profile: ProfileInfo | null;
  login: (password: string) => Promise<void>;
  loginProfile: (pseudonym: string, password: string) => Promise<void>;
  registerProfile: (pseudonym: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

function parseTokenProfile(token: string | null): ProfileInfo | null {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    if (payload.profileId && payload.pseudonym) {
      return { id: payload.profileId, pseudonym: payload.pseudonym };
    }
  } catch {}
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [profile, setProfile] = useState<ProfileInfo | null>(parseTokenProfile(getToken()));

  const login = async (password: string) => {
    const res = await api.auth.verify(password);
    setToken(res.token);
    setTokenState(res.token);
    setProfile(null);
  };

  const loginProfile = async (pseudonym: string, password: string) => {
    const res = await api.profile.login({ pseudonym, password });
    setToken(res.token);
    setTokenState(res.token);
    setProfile(res.profile);
  };

  const registerProfile = async (pseudonym: string, password: string) => {
    const res = await api.profile.register({ pseudonym, password });
    setToken(res.token);
    setTokenState(res.token);
    setProfile(res.profile);
  };

  const logout = () => {
    setToken(null);
    setTokenState(null);
    setProfile(null);
  };

  return createElement(
    AuthContext.Provider,
    { value: { token, profile, login, loginProfile, registerProfile, logout } },
    children
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
