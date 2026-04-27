import { useState, useCallback } from 'react';
import { verifyPassword, setToken, clearToken, getToken } from '../lib/api';

function decodeJwtPayload(token: string): { role: string; jti: string } | null {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export function useAuth() {
  const [token, setTokenState] = useState<string | null>(getToken());

  const payload = token ? decodeJwtPayload(token) : null;
  const role = payload?.role || 'trender';

  const login = useCallback(async (password: string, admin = false) => {
    const { token: newToken } = await verifyPassword(password, admin);
    setToken(newToken);
    setTokenState(newToken);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
  }, []);

  return { token, role, login, logout };
}
