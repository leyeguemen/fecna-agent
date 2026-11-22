import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { AppState } from 'react-native';
import { api, AuthResp, Role, setToken, setUnauthorizedHandler } from './api';
import { storage } from './storage';

type User = { email: string; role: Role; permissions?: string[] };
type Ctx = {
  user: User | null;
  /** ¿Tiene este permiso? (el servidor igual lo valida; aquí solo se muestran u ocultan opciones) */
  can: (permission: string) => boolean;
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
    setUser({ email: r.email, role: r.role, permissions: r.permissions });
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
          const me = await api<{ email: string; role: Role; permissions?: string[] }>('/auth/me'); // valida token y rol vigente
          setUser({ email: me.email, role: me.role, permissions: me.permissions });
        }
      } catch {
        setToken(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [signOut]);

  // Rol y permisos pueden cambiar mientras la app está abierta (un admin los edita): se vuelven a
  // pedir al volver a la app y cada 45 s. Si la cuenta ya no existe, la API responde 401 y se cierra la sesión.
  const loggedIn = !!user;
  useEffect(() => {
    if (!loggedIn) return;
    const refresh = async () => {
      try {
        const me = await api<{ email: string; role: Role; permissions?: string[] }>('/auth/me');
        setUser((u) => (u && (u.role !== me.role || JSON.stringify(u.permissions) !== JSON.stringify(me.permissions))
          ? { ...u, role: me.role, permissions: me.permissions } : u));
      } catch {}
    };
    const timer = setInterval(refresh, 45_000);
    const sub = AppState.addEventListener('change', (state) => { if (state === 'active') refresh(); });
    return () => { clearInterval(timer); sub.remove(); };
  }, [loggedIn]);

  const can = useCallback(
    (permission: string) => (user?.permissions ? user.permissions.includes(permission) : user?.role === 'admin'),
    [user],
  );

  const value = useMemo<Ctx>(() => ({
    user,
    can,
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
  }), [user, can, loading, persist, signOut, pendingLink]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
