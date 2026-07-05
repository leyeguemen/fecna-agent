"use client";

import { useState } from "react";

import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { CompetitionSwimmerItem, WatchResponse } from "@/lib/types";

import { networkAwareMessage } from "./utils";

interface WatchSwimmersProps {
  compId: number;
  swimmers: CompetitionSwimmerItem[];
  watchNames: string[];
  onSaved: (names: string[]) => void;
}

/** Multiselect "seguir nadadores": lista con checkboxes, filtrable por
 * texto. Cada click actualiza el estado local al instante (optimista) y
 * dispara un PUT en segundo plano; si falla, revierte y muestra el error. */
export function WatchSwimmers({ compId, swimmers, watchNames, onSaved }: WatchSwimmersProps) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(() => new Set(watchNames));
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // Al cambiar de campeonato (o tras un guardado exitoso) sincroniza con la
  // verdad del servidor propagada por el padre. Ajustar estado durante el
  // render (en vez de en un efecto) es el patrón recomendado por React para
  // "resetear estado cuando cambia una prop": evita un render extra.
  const [syncedWatchNames, setSyncedWatchNames] = useState(watchNames);
  if (watchNames !== syncedWatchNames) {
    setSyncedWatchNames(watchNames);
    setSelected(new Set(watchNames));
  }

  const filtered = swimmers.filter((s) =>
    s.swimmer_name.toLowerCase().includes(query.trim().toLowerCase()),
  );

  async function toggle(name: string) {
    const token = getToken();
    if (!token || pending.has(name)) return;

    const previous = selected;
    const next = new Set(selected);
    if (next.has(name)) next.delete(name);
    else next.add(name);

    setSelected(next);
    setError(null);
    setPending((p) => new Set(p).add(name));

    try {
      const res = await api.put<WatchResponse>(
        `/competitions/${compId}/watch`,
        { names: Array.from(next) },
        token,
      );
      onSaved(res.names);
    } catch (err) {
      setSelected(previous);
      setError(networkAwareMessage(err, "No se pudo actualizar. Intenta de nuevo."));
    } finally {
      setPending((p) => {
        const copy = new Set(p);
        copy.delete(name);
        return copy;
      });
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border/60 p-4">
      <h2 className="text-sm font-semibold tracking-tight">Seguir nadadores</h2>
      <Input
        type="search"
        placeholder="Buscar nadador…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <ul className="flex max-h-72 flex-col gap-0.5 overflow-y-auto">
        {filtered.length === 0 && (
          <li className="py-2 text-sm text-muted-foreground">Sin resultados.</li>
        )}
        {filtered.map((s) => (
          <li key={`${s.swimmer_name}-${s.club_code}`}>
            <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-accent">
              <input
                type="checkbox"
                checked={selected.has(s.swimmer_name)}
                disabled={pending.has(s.swimmer_name)}
                onChange={() => toggle(s.swimmer_name)}
                className="size-4 shrink-0 accent-primary"
              />
              <span className="flex-1 truncate">{s.swimmer_name}</span>
              <span className="shrink-0 text-xs text-muted-foreground">{s.club_code}</span>
            </label>
          </li>
        ))}
      </ul>

      <p className="text-xs text-muted-foreground">
        {selected.size} nadador{selected.size === 1 ? "" : "es"} seguido{selected.size === 1 ? "" : "s"}.
      </p>
    </div>
  );
}
