"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getToken } from "@/lib/auth";
import { api } from "@/lib/api";
import type { ScheduleItem, ScheduleResponse } from "@/lib/types";

import { formatCountdown, formatFecha, formatHora, networkAwareMessage, parseScheduleDateTime } from "./utils";

const REFRESH_MS = 60_000;

interface AlertsSectionProps {
  compId: number;
  /** true si el usuario tiene sesión iniciada. */
  loggedIn: boolean;
  onLoginClick: () => void;
}

function isPast(item: ScheduleItem, now: Date): boolean {
  const dt = parseScheduleDateTime(item.date, item.start_time);
  return dt !== null && dt.getTime() < now.getTime();
}

/** "Mis alertas": próxima prueba destacada + lista compacta de las
 * inscripciones de los nadadores seguidos. Se refresca cada 60s (refetch +
 * recálculo de cuenta regresiva). Solo se muestra si hay sesión y al menos
 * un nadador seguido en el campeonato (lo decide el padre no montándolo). */
export function AlertsSection({ compId, loggedIn, onLoginClick }: AlertsSectionProps) {
  const [items, setItems] = useState<ScheduleItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    if (!loggedIn) return;
    let cancelled = false;

    async function load() {
      const token = getToken();
      if (!token) return;
      try {
        const data = await api.get<ScheduleResponse>(`/competitions/${compId}/alerts`, token);
        if (!cancelled) {
          setItems(data.items);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(networkAwareMessage(err, "No se pudieron cargar tus alertas."));
      }
    }

    void load();
    const id = window.setInterval(() => {
      void load();
      setNow(new Date());
    }, REFRESH_MS);

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [compId, loggedIn]);

  if (!loggedIn) {
    return (
      <div className="flex flex-col items-start gap-2 rounded-xl border border-dashed border-border/60 p-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <span>Inicia sesión para seguir nadadores y recibir alertas de sus pruebas.</span>
        <Button variant="outline" size="sm" onClick={onLoginClick}>
          Iniciar sesión
        </Button>
      </div>
    );
  }

  if (error) {
    return (
      <p role="alert" className="text-sm text-destructive">
        {error}
      </p>
    );
  }

  if (items === null) {
    return <p className="text-sm text-muted-foreground">Cargando tus alertas…</p>;
  }

  if (items.length === 0) {
    return null;
  }

  const upcoming = items.filter((it) => !isPast(it, now));
  const next = upcoming[0] ?? null;

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold tracking-tight">Mis alertas</h2>

      {next ? (
        <div className="flex flex-col gap-1 rounded-xl border border-primary/30 bg-primary/5 p-4">
          <span className="text-xs font-medium tracking-wide text-primary uppercase">
            Próxima prueba
          </span>
          <p className="font-medium">
            {next.swimmer_name} · {next.event_label}
          </p>
          <p className="text-sm text-muted-foreground">
            Serie {next.heat} · Carril {next.lane} · {formatFecha(next.date)}, {formatHora(next.start_time)}
          </p>
          <p className="text-sm font-semibold">
            {parseScheduleDateTime(next.date, next.start_time)
              ? formatCountdown(parseScheduleDateTime(next.date, next.start_time)!, now)
              : "Hora por confirmar"}
          </p>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          No quedan pruebas pendientes para tus nadadores seguidos.
        </p>
      )}

      <ul className="flex flex-col gap-1">
        {items.map((it, i) => {
          const past = isPast(it, now);
          const isNext = next !== null && it === next;
          return (
            <li
              key={`${it.event_number}-${it.swimmer_name}-${i}`}
              className={`flex flex-wrap items-center gap-x-2 gap-y-0.5 rounded-lg px-2 py-1.5 text-sm ${
                past ? "text-muted-foreground/60" : isNext ? "bg-primary/5 font-medium" : ""
              }`}
            >
              <span>{formatFecha(it.date)}</span>
              <span aria-hidden="true">·</span>
              <span>{formatHora(it.start_time)}</span>
              <span aria-hidden="true">·</span>
              <span>{it.swimmer_name}</span>
              <span aria-hidden="true">·</span>
              <span className="text-muted-foreground">{it.event_label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
