// Cliente de la API de NATIA. El token vive en memoria (y en SecureStore, ver auth.tsx).
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

let token: string | null = null;
let onUnauthorized: () => void = () => {};

export const setToken = (t: string | null) => { token = t; };
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn; };

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

// Render free "duerme" el servicio: el primer request puede tardar ~50 s.
const TIMEOUT_MS = 70_000;

export async function api<T = any>(
  path: string,
  opts: { method?: string; body?: unknown; form?: FormData; auth?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.auth !== false && token) headers.Authorization = `Bearer ${token}`;
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: opts.method ?? (opts.body || opts.form ? 'POST' : 'GET'),
      headers,
      body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
      signal: ctrl.signal,
    });
  } catch {
    throw new ApiError(0, 'No se pudo conectar con el servidor. Reintenta en unos segundos.');
  } finally {
    clearTimeout(timer);
  }

  if (res.status === 401 && opts.auth !== false && token) onUnauthorized();
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') detail = j.detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export type Role = 'user' | 'admin';
export type AuthResp = { token: string; email: string; role: Role; permissions?: string[] };
export type Item = Record<string, any>;

/** POST multipart que devuelve una imagen (la ficha para redes), con la sesión actual. */
export async function apiImage(path: string, form: FormData): Promise<ArrayBuffer> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: 'POST', body: form, signal: ctrl.signal,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw new ApiError(0, 'No se pudo conectar con el servidor. Reintenta en unos segundos.');
  } finally {
    clearTimeout(timer);
  }
  if (res.status === 401) onUnauthorized();
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try { const j = await res.json(); if (typeof j.detail === 'string') detail = j.detail; } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.arrayBuffer();
}

/** GET que devuelve texto (p. ej. la ficha HTML descargable), con la sesión actual. */
export async function apiText(path: string): Promise<string> {
  const res = await fetch(`${API_URL}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (res.status === 401) onUnauthorized();
  if (!res.ok) throw new ApiError(res.status, `Error ${res.status}`);
  return res.text();
}
