import { createContext, useContext, useEffect, useState } from 'react';
import * as authApi from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('merchaudit_token');
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => localStorage.removeItem('merchaudit_token'))
      .finally(() => setLoading(false));
  }, []);

  async function signIn(email, password) {
    const token = await authApi.login(email, password);
    localStorage.setItem('merchaudit_token', token);
    const profile = await authApi.me();
    setUser(profile);
    return profile;
  }

  function signOut() {
    localStorage.removeItem('merchaudit_token');
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
