import * as SecureStore from 'expo-secure-store';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, AuthResp, Role, setToken, setUnauthorizedHandler } from './api';

type User = { email: string; role: Role };
type Ctx = {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const KEY = 'fecna_session';
const AuthCtx = createContext<Ctx>(null as unknown as Ctx);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const persist = useCallback(async (r: AuthResp) => {
    setToken(r.token);
    setUser({ email: r.email, role: r.role });
    await SecureStore.setItemAsync(KEY, JSON.stringify(r));
  }, []);

  const signOut = useCallback(async () => {
    setToken(null);
    setUser(null);
    await SecureStore.deleteItemAsync(KEY);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => { signOut(); }); // token vencido → a login
    (async () => {
      try {
        const raw = await SecureStore.getItemAsync(KEY);
        if (raw) {
          const r: AuthResp = JSON.parse(raw);
          setToken(r.token);
          const me = await api<{ email: string; role: Role }>('/auth/me'); // valida token y rol vigente
          setUser({ email: me.email, role: me.role });
        }
      } catch {
        setToken(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [signOut]);

  const value = useMemo<Ctx>(() => ({
    user,
    loading,
    signIn: async (email, password) =>
      persist(await api<AuthResp>('/auth/login', { body: { email, password }, auth: false })),
    signUp: async (email, password) =>
      persist(await api<AuthResp>('/auth/register', { body: { email, password }, auth: false })),
    signOut,
  }), [user, loading, persist, signOut]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
