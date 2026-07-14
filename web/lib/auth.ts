/**
 * Sesión de usuario: token en localStorage + store reactivo.
 *
 * Mismo patrón que `components/theme-toggle.tsx` (listeners + useSyncExternalStore)
 * para evitar dependencias extra de manejo de estado. El token vive en
 * `localStorage` bajo `TOKEN_KEY`; `getToken()` es la función que deben usar
 * otros módulos (p.ej. B5, watch/upload) para leerlo y pasarlo a `api.*`.
 *
 * Convención elegida para llamadas autenticadas: pasar el token como último
 * argumento posicional de `api.get/post/put/delete` (ya soportado en
 * `lib/api.ts`). `authHeaders()` se expone además por si algún caller arma
 * su propio `fetch`/`Headers` en vez de usar `api`.
 */

import { useEffect, useSyncExternalStore } from "react";

import { api, ApiError } from "@/lib/api";
import type { AuthResponse, MeResponse, UserRole } from "@/lib/types";

const TOKEN_KEY = "fecna_token";
const USER_KEY = "fecna_user";

export interface SessionUser {
  email: string;
  role: UserRole;
}

interface AuthState {
  user: SessionUser | null;
  loading: boolean;
}

// Sin token conocido, el primer render es explícitamente anónimo: así el
// acceso "Ingresar" aparece desde SSR y no depende de un efecto del cliente.
let state: AuthState = { user: null, loading: false };
// React compara snapshots por identidad. Este valor debe conservar la misma
// referencia entre renders SSR; devolver un objeto literal desde
// getServerSnapshot provoca el aviso de caché y puede iniciar un bucle.
const SERVER_SNAPSHOT: AuthState = { user: null, loading: false };
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((listener) => listener());
}

function subscribe(callback: () => void) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

function getSnapshot(): AuthState {
  return state;
}

function getServerSnapshot(): AuthState {
  return SERVER_SNAPSHOT;
}

function setState(patch: Partial<AuthState>) {
  state = { ...state, ...patch };
  notify();
}

/** Token guardado en localStorage, o `null` si no hay sesión (SSR-safe). */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

function isSessionUser(value: unknown): value is SessionUser {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<SessionUser>;
  return (
    typeof candidate.email === "string" &&
    (candidate.role === "user" || candidate.role === "admin")
  );
}

function storeUser(user: SessionUser) {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/** Recupera el perfil cacheado. Para sesiones creadas antes de USER_KEY,
 * obtiene email/rol del payload JWT solo como fallback visual; la API sigue
 * siendo quien valida criptográficamente el token. */
function readStoredUser(token: string): SessionUser | null {
  try {
    const stored = window.localStorage.getItem(USER_KEY);
    if (stored) {
      const parsed: unknown = JSON.parse(stored);
      if (isSessionUser(parsed)) return parsed;
    }

    const payload = token.split(".")[1];
    if (!payload) return null;
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const decoded: unknown = JSON.parse(window.atob(padded));
    return isSessionUser(decoded) ? decoded : null;
  } catch {
    return null;
  }
}

/** Encabezado `Authorization: Bearer ...` para callers que arman su propio fetch. */
export function authHeaders(token: string = getToken() ?? ""): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

let initialized = false;

/** Valida el token guardado contra /auth/me. Se ejecuta una sola vez, al
 * primer uso de useUser en el cliente. Token inválido/expirado -> se
 * limpia en silencio (sin mostrar error). */
async function initFromStorage() {
  if (initialized) return;
  initialized = true;

  const token = getToken();
  if (!token) {
    window.localStorage.removeItem(USER_KEY);
    setState({ user: null, loading: false });
    return;
  }

  const cachedUser = readStoredUser(token);
  setState({ user: cachedUser, loading: true });

  try {
    const me = await api.get<MeResponse>("/auth/me", token);
    // No sobrescribir un login/logout ocurrido mientras /auth/me estaba en curso.
    if (getToken() !== token) return;
    const user = { email: me.email, role: me.role };
    storeUser(user);
    setState({ user, loading: false });
  } catch (err) {
    if (getToken() !== token) return;
    // Solo un rechazo HTTP real (401/token inválido) invalida la sesión.
    // Un fallo de red conserva el perfil cacheado y permite seguir mostrando
    // la sesión; se revalidará en el próximo arranque.
    if (err instanceof ApiError && err.kind === "http") {
      clearToken();
      setState({ user: null, loading: false });
      return;
    }
    setState({ user: cachedUser, loading: false });
  }
}

async function login(email: string, password: string): Promise<void> {
  const res = await api.post<AuthResponse>("/auth/login", { email, password });
  setToken(res.token);
  const user = { email: res.email, role: res.role };
  storeUser(user);
  setState({ user, loading: false });
}

async function register(email: string, password: string): Promise<void> {
  const res = await api.post<AuthResponse>("/auth/register", { email, password });
  setToken(res.token);
  const user = { email: res.email, role: res.role };
  storeUser(user);
  setState({ user, loading: false });
}

function logout(): void {
  clearToken();
  setState({ user: null, loading: false });
}

export function useUser() {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    void initFromStorage();
  }, []);

  return {
    user: snapshot.user,
    loading: snapshot.loading,
    login,
    register,
    logout,
  };
}
