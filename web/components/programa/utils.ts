/**
 * Helpers compartidos de la página Programa/Alertas: mensajes de error de
 * red (mismo patrón que `ranking-section.tsx`) y utilidades de fecha/hora
 * para el cronograma y las alertas ("faltan X min/h").
 *
 * `date` llega como `YYYY-MM-DD` y `start_time` como `HH:MM` 24h (ver
 * `fecna_agent/programa.py::_to_24h` y `api/routers/competitions.py`).
 */

import { ApiError } from "@/lib/api";

export function networkAwareMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    return err.kind === "network" ? "No se pudo conectar con el servidor." : err.detail;
  }
  return fallback;
}

const FECHA_FMT = new Intl.DateTimeFormat("es-ES", {
  weekday: "short",
  day: "numeric",
  month: "short",
});

/** "2026-07-05" -> "dom, 5 jul" (es-ES). */
export function formatFecha(date: string | null): string {
  if (!date) return "Fecha por confirmar";
  const d = new Date(`${date}T00:00:00`);
  if (Number.isNaN(d.getTime())) return date;
  return FECHA_FMT.format(d);
}

/** "08:00" -> "08:00". `null` -> "Por confirmar". */
export function formatHora(time: string | null): string {
  return time ?? "Por confirmar";
}

/** Combina fecha + hora en un `Date` local, o `null` si falta alguno o el
 * combo no es válido. */
export function parseScheduleDateTime(date: string | null, time: string | null): Date | null {
  if (!date || !time) return null;
  const dt = new Date(`${date}T${time}:00`);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

/** "Faltan X min" / "Faltan X h Y min" / "En curso" / "Finalizada", según
 * la diferencia entre `target` y `now`. */
export function formatCountdown(target: Date, now: Date): string {
  const diffMs = target.getTime() - now.getTime();

  if (diffMs > 0) {
    const totalMin = Math.round(diffMs / 60000);
    if (totalMin < 1) return "Empieza en instantes";
    if (totalMin < 60) return `Faltan ${totalMin} min`;
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    return m > 0 ? `Faltan ${h} h ${m} min` : `Faltan ${h} h`;
  }

  const elapsedMin = Math.round(-diffMs / 60000);
  return elapsedMin < 60 ? "En curso" : "Finalizada";
}

const UPLOAD_STATUS_LABELS: Record<string, string> = {
  created: "creado",
  updated: "actualizado",
  unchanged: "sin cambios",
};

export function formatUploadStatus(status: string): string {
  return UPLOAD_STATUS_LABELS[status] ?? status;
}
