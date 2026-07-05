"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import type { CatalogsResponse, RankingResponse } from "@/lib/types";

import { RankingFilters, type FilterKey } from "./ranking-filters";
import { RankingResults } from "./ranking-results";
import { RankingSkeleton } from "./ranking-skeleton";

const DEFAULT_POOL = "LC";
const DEFAULT_GENDER = "M";
const DEFAULT_LIMIT = 25;
const LIMIT_STEP = 25;
const MAX_LIMIT = 100;

function pickDefaultEventId(catalogs: CatalogsResponse): string | null {
  if (catalogs.pruebas.length === 0) return null;
  const preferred = catalogs.pruebas.find(
    (p) => /50/.test(p.nombre) && /libre/i.test(p.nombre),
  );
  return (preferred ?? catalogs.pruebas[0]).id;
}

function networkAwareMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    return err.kind === "network" ? "No se pudo conectar con el servidor." : err.detail;
  }
  return fallback;
}

export function RankingSection() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [catalogs, setCatalogs] = useState<CatalogsResponse | null>(null);
  const [catalogsError, setCatalogsError] = useState<string | null>(null);
  const [catalogsRetryToken, setCatalogsRetryToken] = useState(0);

  const [ranking, setRanking] = useState<RankingResponse | null>(null);
  const [rankingStatus, setRankingStatus] = useState<"idle" | "loading" | "error" | "done">(
    "idle",
  );
  const [rankingError, setRankingError] = useState<string | null>(null);
  const [rankingRetryToken, setRankingRetryToken] = useState(0);

  const eventId = searchParams.get("event_id") ?? "";
  const pool = searchParams.get("pool") ?? DEFAULT_POOL;
  const gender = searchParams.get("gender") ?? DEFAULT_GENDER;
  const category = searchParams.get("category") ?? "";
  const rawLimit = Number(searchParams.get("limit"));
  const limit =
    Number.isFinite(rawLimit) && rawLimit > 0 ? Math.min(rawLimit, MAX_LIMIT) : DEFAULT_LIMIT;

  // Catálogos: una sola carga (no dependen de los filtros).
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setCatalogsError(null);
      try {
        const data = await api.get<CatalogsResponse>("/catalogs");
        if (!cancelled) setCatalogs(data);
      } catch (err) {
        if (!cancelled) {
          setCatalogsError(networkAwareMessage(err, "No se pudieron cargar los filtros."));
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [catalogsRetryToken]);

  // Si la URL no trae prueba (primera visita), fijamos un default sensible
  // en cuanto los catálogos estén listos, para que la tabla muestre datos.
  useEffect(() => {
    if (!catalogs || eventId) return;
    const defaultEvent = pickDefaultEventId(catalogs);
    if (!defaultEvent) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set("event_id", defaultEvent);
    if (!params.get("pool")) params.set("pool", DEFAULT_POOL);
    if (!params.get("gender")) params.set("gender", DEFAULT_GENDER);
    router.replace(`/?${params.toString()}`, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalogs, eventId]);

  // Ranking: se recarga cuando cambian filtros o límite.
  useEffect(() => {
    if (!eventId) return;
    let cancelled = false;

    async function load() {
      setRankingStatus("loading");
      setRankingError(null);

      const qs = new URLSearchParams({ event_id: eventId, pool, gender, limit: String(limit) });
      if (category) qs.set("category", category);

      try {
        const data = await api.get<RankingResponse>(`/rankings?${qs.toString()}`);
        if (cancelled) return;
        setRanking(data);
        setRankingStatus("done");
      } catch (err) {
        if (cancelled) return;
        setRankingStatus("error");
        setRankingError(networkAwareMessage(err, "No se pudo cargar el ranking."));
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [eventId, pool, gender, category, limit, rankingRetryToken]);

  const updateFilter = useCallback(
    (key: FilterKey, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) params.set(key, value);
      else params.delete(key);
      params.delete("limit"); // cambiar un filtro reinicia la paginación
      router.replace(`/?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const loadMore = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("limit", String(Math.min(limit + LIMIT_STEP, MAX_LIMIT)));
    router.replace(`/?${params.toString()}`, { scroll: false });
  }, [limit, router, searchParams]);

  if (catalogsError) {
    return (
      <ErrorState message={catalogsError} onRetry={() => setCatalogsRetryToken((t) => t + 1)} />
    );
  }

  if (!catalogs) {
    return <RankingSkeleton />;
  }

  const showLoadMore = ranking !== null && limit < MAX_LIMIT && ranking.items.length >= limit;

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold tracking-tight">Ranking</h2>

      <RankingFilters
        catalogs={catalogs}
        eventId={eventId}
        pool={pool}
        gender={gender}
        category={category}
        onChange={updateFilter}
      />

      {rankingStatus === "loading" && <RankingSkeleton />}

      {rankingStatus === "error" && (
        <ErrorState
          message={rankingError ?? "Ocurrió un error inesperado."}
          onRetry={() => setRankingRetryToken((t) => t + 1)}
        />
      )}

      {rankingStatus === "done" && ranking && ranking.items.length === 0 && (
        <EmptyState />
      )}

      {rankingStatus === "done" && ranking && ranking.items.length > 0 && (
        <>
          <RankingResults items={ranking.items} />
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">
              {ranking.total} resultado{ranking.total === 1 ? "" : "s"}
            </span>
            {showLoadMore && (
              <Button variant="outline" size="sm" onClick={loadMore}>
                Cargar más
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border/60 p-10 text-center">
      <span className="text-2xl" aria-hidden="true">
        🔍
      </span>
      <p className="font-medium">No hay resultados para estos filtros.</p>
      <p className="text-sm text-muted-foreground">
        Prueba con otra prueba, categoría o género.
      </p>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-destructive/40 p-10 text-center">
      <p className="text-sm text-destructive">{message}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Reintentar
      </Button>
    </div>
  );
}
