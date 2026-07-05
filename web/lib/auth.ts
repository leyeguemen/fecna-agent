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

export interface SessionUser {
  email: string;
  role: UserRole;
}

interface AuthState {
  user: SessionUser | null;
  loading: boolean;
}

let state: AuthState = { user: null, loading: true };
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
  return { user: null, loading: true };
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
    setState({ user: null, loading: false });
    return;
  }

  try {
    const me = await api.get<MeResponse>("/auth/me", token);
    setState({ user: { email: me.email, role: me.role }, loading: false });
  } catch (err) {
    // Solo un rechazo HTTP real (401/token inválido) invalida la sesión.
    // Un fallo de red no invalida la sesión guardada; se revalidará en el próximo arranque.
    if (err instanceof ApiError && err.kind === "http") {
      clearToken();
    }
    setState({ user: null, loading: false });
  }
}

async function login(email: string, password: string): Promise<void> {
  const res = await api.post<AuthResponse>("/auth/login", { email, password });
  setToken(res.token);
  setState({ user: { email: res.email, role: res.role }, loading: false });
}

async function register(email: string, password: string): Promise<void> {
  const res = await api.post<AuthResponse>("/auth/register", { email, password });
  setToken(res.token);
  setState({ user: { email: res.email, role: res.role }, loading: false });
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
