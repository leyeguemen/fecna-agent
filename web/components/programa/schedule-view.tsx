"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

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
import { api } from "@/lib/api";
import type {
  CompetitionClubsResponse,
  CompetitionSwimmerItem,
  ScheduleItem,
  ScheduleResponse,
} from "@/lib/types";

import { formatFecha, formatHora, networkAwareMessage } from "./utils";

const ALL = "__TODOS__";

interface ScheduleViewProps {
  compId: number;
  swimmers: CompetitionSwimmerItem[];
  watchedNames: Set<string>;
}

type Status = "loading" | "error" | "done";

export function ScheduleView({ compId, swimmers, watchedNames }: ScheduleViewProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const club = searchParams.get("club") ?? "";
  const swimmer = searchParams.get("swimmer") ?? "";

  const [clubs, setClubs] = useState<string[]>([]);
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api
      .get<CompetitionClubsResponse>(`/competitions/${compId}/clubs`)
      .then((data) => {
        if (!cancelled) setClubs(data.items);
      })
      .catch(() => {
        // Filtro secundario: si falla, simplemente no se ofrece el filtro de club.
      });
    return () => {
      cancelled = true;
    };
  }, [compId]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setStatus("loading");
      setError(null);
      const qs = new URLSearchParams();
      if (club) qs.set("club", club);
      if (swimmer) qs.set("swimmer", swimmer);
      const query = qs.toString();

      try {
        const data = await api.get<ScheduleResponse>(
          `/competitions/${compId}/schedule${query ? `?${query}` : ""}`,
        );
        if (cancelled) return;
        setItems(data.items);
        setStatus("done");
      } catch (err) {
        if (cancelled) return;
        setStatus("error");
        setError(networkAwareMessage(err, "No se pudo cargar el cronograma."));
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [compId, club, swimmer, retryToken]);

  const updateFilter = useCallback(
    (key: "club" | "swimmer", value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) params.set(key, value);
      else params.delete(key);
      router.replace(`/programa?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold tracking-tight">Cronograma</h2>

      <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
        <Select
          value={club || ALL}
          onValueChange={(v) => updateFilter("club", v === ALL ? null : (v as string))}
        >
          <SelectTrigger className="w-full sm:w-48">
            <SelectValue placeholder="Club" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos los clubes</SelectItem>
            {clubs.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={swimmer || ALL}
          onValueChange={(v) => updateFilter("swimmer", v === ALL ? null : (v as string))}
        >
          <SelectTrigger className="w-full sm:w-56">
            <SelectValue placeholder="Nadador" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos los nadadores</SelectItem>
            {swimmers.map((s) => (
              <SelectItem key={`${s.swimmer_name}-${s.club_code}`} value={s.swimmer_name}>
                {s.swimmer_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {status === "loading" && (
        <p className="text-sm text-muted-foreground">Cargando cronograma…</p>
      )}

      {status === "error" && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-destructive/40 p-10 text-center">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={() => setRetryToken((t) => t + 1)}>
            Reintentar
          </Button>
        </div>
      )}

      {status === "done" && items.length === 0 && (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border/60 p-10 text-center">
          <span className="text-2xl" aria-hidden="true">
            🏊
          </span>
          <p className="font-medium">No hay pruebas para estos filtros.</p>
        </div>
      )}

      {status === "done" && items.length > 0 && (
        <>
          <div className="hidden overflow-hidden rounded-xl border border-border/60 md:block">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Fecha</TableHead>
                  <TableHead>Jornada</TableHead>
                  <TableHead>Hora</TableHead>
                  <TableHead>Nº</TableHead>
                  <TableHead>Prueba</TableHead>
                  <TableHead>Cat.</TableHead>
                  <TableHead>Serie</TableHead>
                  <TableHead>Carril</TableHead>
                  <TableHead>Nadador</TableHead>
                  <TableHead>Club</TableHead>
                  <TableHead>Semilla</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item, i) => (
                  <TableRow key={`${item.event_number}-${item.swimmer_name}-${i}`}>
                    <TableCell>{formatFecha(item.date)}</TableCell>
                    <TableCell>{item.session_no}</TableCell>
                    <TableCell>{formatHora(item.start_time)}</TableCell>
                    <TableCell>{item.event_number}</TableCell>
                    <TableCell>{item.event_label}</TableCell>
                    <TableCell>{item.category}</TableCell>
                    <TableCell>{item.heat}</TableCell>
                    <TableCell>{item.lane}</TableCell>
                    <TableCell>
                      <SwimmerName item={item} watched={watchedNames.has(item.swimmer_name)} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">{item.club_code}</TableCell>
                    <TableCell className="font-mono text-muted-foreground">
                      {item.seed ?? "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <ul className="flex flex-col gap-2 md:hidden">
            {items.map((item, i) => (
              <li
                key={`${item.event_number}-${item.swimmer_name}-${i}`}
                className="rounded-xl border border-border/60 bg-card p-3 ring-1 ring-foreground/5"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-base font-semibold">
                    {formatHora(item.start_time)}
                  </span>
                  <span className="text-xs text-muted-foreground">{formatFecha(item.date)}</span>
                </div>
                <p className="font-medium">{item.event_label}</p>
                <p className="text-sm text-muted-foreground">
                  <SwimmerName item={item} watched={watchedNames.has(item.swimmer_name)} /> ·{" "}
                  {item.club_code}
                </p>
                <p className="text-xs text-muted-foreground">
                  Serie {item.heat} · Carril {item.lane} · Cat. {item.category}
                </p>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function SwimmerName({ item, watched }: { item: ScheduleItem; watched: boolean }) {
  const label = (
    <>
      {watched && (
        <span aria-label="Nadador seguido" title="Nadador seguido">
          🔔{" "}
        </span>
      )}
      {item.swimmer_name}
    </>
  );

  if (!item.swimmer_id) return label;

  return (
    <Link href={`/nadador/${item.swimmer_id}`} className="hover:underline">
      {label}
    </Link>
  );
}
