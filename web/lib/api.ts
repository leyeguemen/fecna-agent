/**
 * Cliente fetch tipado para la API FECNA.
 *
 * Base URL configurable vía `NEXT_PUBLIC_API_URL` (por defecto apunta al
 * backend local en desarrollo). Lanza `ApiError` con el `detail` que
 * devuelve FastAPI (`{"detail": "..."}`) cuando la respuesta no es 2xx
 * (`kind: "http"`), o con un mensaje en español cuando el fetch falla a
 * nivel de red —DNS, CORS, conexión rechazada, timeout/abort— (`kind:
 * "network"`, `status: 0`). Los llamadores pueden discriminar por `kind`
 * sin recurrir a `instanceof TypeError`.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;
  kind: "http" | "network";

  constructor(status: number, detail: string, kind: "http" | "network" = "http") {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.kind = kind;
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

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  } catch {
    // fetch solo rechaza por fallos de red: DNS, conexión rechazada, CORS,
    // abort/timeout. Nunca por respuestas HTTP no-2xx (eso lo maneja el
    // bloque de abajo), así que aquí siempre es un problema de conectividad.
    throw new ApiError(0, "No se pudo conectar con el servidor.", "network");
  }

  if (!res.ok) {
    throw new ApiError(res.status, await extractDetail(res), "http");
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
