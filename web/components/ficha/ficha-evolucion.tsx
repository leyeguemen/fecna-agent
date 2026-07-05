"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, ApiError } from "@/lib/api";
import type { SwimmerHistoryResponse, SwimmerTopEvent } from "@/lib/types";

type Status = "idle" | "loading" | "error" | "done";

const POOL_LABELS: Record<string, string> = {
  LC: "Piscina larga (LC)",
  SC: "Piscina corta (SC)",
};

function optionKey(event: Pick<SwimmerTopEvent, "event_id" | "pool">): string {
  return `${event.event_id}|${event.pool}`;
}

function networkAwareMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    return err.kind === "network" ? "No se pudo conectar con el servidor." : err.detail;
  }
  return fallback;
}

/** Sección secundaria y colapsable: historial de tiempos de una prueba
 * elegida entre las mejores pruebas del nadador. Cliente porque depende de
 * interacción (selector) — no forma parte de la infografía imprimible. */
export function FichaEvolucion({
  swimmerId,
  topEvents,
}: {
  swimmerId: string;
  topEvents: SwimmerTopEvent[];
}) {
  const [selected, setSelected] = useState(() =>
    topEvents.length > 0 ? optionKey(topEvents[0]) : "",
  );
  const [history, setHistory] = useState<SwimmerHistoryResponse | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  const selectedEvent = useMemo(
    () => topEvents.find((e) => optionKey(e) === selected) ?? null,
    [topEvents, selected],
  );

  useEffect(() => {
    if (!selectedEvent) return;
    let cancelled = false;

    async function load() {
      setStatus("loading");
      setErrorMessage(null);
      const qs = new URLSearchParams({
        event_id: selectedEvent!.event_id,
        pool: selectedEvent!.pool,
      });
      try {
        const data = await api.get<SwimmerHistoryResponse>(
          `/swimmers/${swimmerId}/history?${qs.toString()}`,
        );
        if (cancelled) return;
        setHistory(data);
        setStatus("done");
      } catch (err) {
        if (cancelled) return;
        setStatus("error");
        setErrorMessage(networkAwareMessage(err, "No se pudo cargar el historial."));
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [selectedEvent, swimmerId, retryToken]);

  if (topEvents.length === 0) return null;

  return (
    <details className="group rounded-xl border border-border/60 print:hidden">
      <summary className="cursor-pointer list-none px-4 py-3 text-sm font-semibold tracking-tight select-none">
        <span className="mr-2 inline-block transition-transform group-open:rotate-90">▶</span>
        Evolución de tiempos
      </summary>

      <div className="flex flex-col gap-4 border-t border-border/60 p-4">
        <Select value={selected} onValueChange={(v) => setSelected(v as string)}>
          <SelectTrigger className="w-full sm:w-72">
            <SelectValue placeholder="Elige una prueba" />
          </SelectTrigger>
          <SelectContent>
            {topEvents.map((event) => (
              <SelectItem key={optionKey(event)} value={optionKey(event)}>
                {event.event_name} · {POOL_LABELS[event.pool] ?? event.pool}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {status === "loading" && (
          <p className="text-sm text-muted-foreground">Cargando historial…</p>
        )}

        {status === "error" && (
          <div className="flex flex-col items-start gap-2">
            <p role="alert" className="text-sm text-destructive">
              {errorMessage}
            </p>
            <Button variant="outline" size="sm" onClick={() => setRetryToken((t) => t + 1)}>
              Reintentar
            </Button>
          </div>
        )}

        {status === "done" && history && history.items.length === 0 && (
          <p className="text-sm text-muted-foreground">Sin historial para esta prueba.</p>
        )}

        {status === "done" && history && history.items.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-border/60">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Fecha</TableHead>
                  <TableHead>Tiempo</TableHead>
                  <TableHead>Piscina</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.items.map((item, i) => (
                  <TableRow key={`${item.date}-${item.time_ms}-${i}`}>
                    <TableCell className="text-muted-foreground">{item.date}</TableCell>
                    <TableCell className="font-mono font-semibold">{item.time}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {POOL_LABELS[item.pool] ?? item.pool}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </details>
  );
}
