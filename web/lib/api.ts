/**
 * Cliente fetch tipado para la API FECNA.
 *
 * Base URL configurable vía `NEXT_PUBLIC_API_URL` (por defecto apunta al
 * backend local en desarrollo). Lanza `ApiError` con el `detail` que
 * devuelve FastAPI (`{"detail": "..."}`) cuando la respuesta no es 2xx.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function extractDetail(res: Response): Promise<string> {
  try {
    const body = await res.clone().json();
    if (body && typeof body.detail === "string") return body.detail;
    if (body && Array.isArray(body.detail)) {
      // Errores de validación de FastAPI/Pydantic: lista de {msg, loc, ...}.
      return body.detail.map((e: { msg?: string }) => e.msg).filter(Boolean).join(" | ") || res.statusText;
    }
  } catch {
    // Cuerpo no era JSON; usamos el texto de estado HTTP.
  }
  return res.statusText || `Error ${res.status}`;
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    throw new ApiError(res.status, await extractDetail(res));
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, token?: string) => request<T>(path, { method: "GET" }, token),

  post: <T>(path: string, body?: unknown, token?: string) =>
    request<T>(
      path,
      { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined },
      token,
    ),

  put: <T>(path: string, body?: unknown, token?: string) =>
    request<T>(
      path,
      { method: "PUT", body: body !== undefined ? JSON.stringify(body) : undefined },
      token,
    ),

  delete: <T>(path: string, token?: string) => request<T>(path, { method: "DELETE" }, token),
};
