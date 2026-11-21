import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, AuthResp, Role, setToken, setUnauthorizedHandler } from './api';
import { storage } from './storage';

type User = { email: string; role: Role };
type Ctx = {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, acceptTerms: boolean) => Promise<void>;
  signOut: () => Promise<void>;
  pendingLink: boolean; // recién registrado: ofrecer vincular su nadador
  clearPendingLink: () => void;
};

const KEY = 'fecna_session';
const AuthCtx = createContext<Ctx>(null as unknown as Ctx);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingLink, setPendingLink] = useState(false);

  const persist = useCallback(async (r: AuthResp) => {
    setToken(r.token);
    setUser({ email: r.email, role: r.role });
    await storage.set(KEY, JSON.stringify(r));
  }, []);

  const signOut = useCallback(async () => {
    setToken(null);
    setUser(null);
    await storage.remove(KEY);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => { signOut(); }); // token vencido → a login
    (async () => {
      try {
        const raw = await storage.get(KEY);
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
    signUp: async (email, password, acceptTerms) => {
      const r = await api<AuthResp>('/auth/register', { body: { email, password, accept_terms: acceptTerms }, auth: false });
      setPendingLink(true);
      await persist(r);
    },
    signOut,
    pendingLink,
    clearPendingLink: () => setPendingLink(false),
  }), [user, loading, persist, signOut, pendingLink]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
