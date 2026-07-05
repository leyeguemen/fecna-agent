"use client";

import { useRouter } from "next/navigation";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { RankingItem } from "@/lib/types";

const MEDALS: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };

/** Tabla (desktop) + lista de tarjetas (móvil) para los resultados del
 * ranking. Cada fila/tarjeta navega a la ficha del nadador. */
export function RankingResults({ items }: { items: RankingItem[] }) {
  const router = useRouter();

  function goTo(id: string) {
    router.push(`/nadador/${id}`);
  }

  return (
    <>
      <div className="hidden overflow-hidden rounded-xl border border-border/60 md:block">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-16">Puesto</TableHead>
              <TableHead>Tiempo</TableHead>
              <TableHead>Nadador</TableHead>
              <TableHead>Club</TableHead>
              <TableHead>Liga</TableHead>
              <TableHead>Fecha</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow
                key={`${item.swimmer_id}-${item.pos}`}
                tabIndex={0}
                role="button"
                aria-label={`Ver ficha de ${item.swimmer_name}`}
                onClick={() => goTo(item.swimmer_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") goTo(item.swimmer_id);
                }}
                className="cursor-pointer outline-none focus-visible:bg-muted/50"
              >
                <TableCell className="font-medium">
                  {MEDALS[item.pos] ? (
                    <span aria-hidden="true">{MEDALS[item.pos]}</span>
                  ) : (
                    item.pos
                  )}
                  <span className="sr-only"> Puesto {item.pos}</span>
                </TableCell>
                <TableCell className="font-mono text-base font-semibold">{item.time}</TableCell>
                <TableCell>{item.swimmer_name}</TableCell>
                <TableCell className="text-muted-foreground">{item.club}</TableCell>
                <TableCell className="text-muted-foreground">{item.league}</TableCell>
                <TableCell className="text-muted-foreground">{item.date}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <ul className="flex flex-col gap-2 md:hidden">
        {items.map((item) => (
          <li key={`${item.swimmer_id}-${item.pos}`}>
            <button
              type="button"
              onClick={() => goTo(item.swimmer_id)}
              aria-label={`Ver ficha de ${item.swimmer_name}`}
              className="flex w-full items-center gap-3 rounded-xl border border-border/60 bg-card p-3 text-left ring-1 ring-foreground/5 transition-colors active:bg-muted"
            >
              <span className="flex w-9 shrink-0 items-center justify-center text-lg font-semibold tabular-nums">
                {MEDALS[item.pos] ?? item.pos}
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate font-medium">{item.swimmer_name}</span>
                <span className="truncate text-xs text-muted-foreground">{item.club}</span>
              </span>
              <span className="shrink-0 font-mono text-base font-semibold">{item.time}</span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
