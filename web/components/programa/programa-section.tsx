"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AuthDialog } from "@/components/auth/auth-dialog";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { getToken, useUser } from "@/lib/auth";
import type {
  CompetitionsResponse,
  CompetitionSummary,
  CompetitionSwimmerItem,
  CompetitionSwimmersResponse,
  CompetitionUploadResponse,
  WatchResponse,
} from "@/lib/types";

import { AdminPanel } from "./admin-panel";
import { AlertsSection } from "./alerts-section";
import { CompetitionSelector } from "./competition-selector";
import { ProgramaEmptyState } from "./empty-state";
import { ProgramaSkeleton } from "./programa-skeleton";
import { ScheduleView } from "./schedule-view";
import { networkAwareMessage } from "./utils";
import { WatchSwimmers } from "./watch-swimmers";

export function ProgramaSection() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useUser();
  const [authOpen, setAuthOpen] = useState(false);

  const [competitions, setCompetitions] = useState<CompetitionSummary[] | null>(null);
  const [competitionsError, setCompetitionsError] = useState<string | null>(null);
  const [competitionsRetryToken, setCompetitionsRetryToken] = useState(0);

  const [swimmers, setSwimmers] = useState<CompetitionSwimmerItem[]>([]);
  const [watchNames, setWatchNames] = useState<string[]>([]);

  const compIdParam = searchParams.get("comp");
  const compId = compIdParam ? Number(compIdParam) : null;

  // Campeonatos: carga única (no depende de filtros).
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setCompetitionsError(null);
      try {
        const data = await api.get<CompetitionsResponse>("/competitions");
        if (!cancelled) setCompetitions(data.items);
      } catch (err) {
        if (!cancelled) {
          setCompetitionsError(networkAwareMessage(err, "No se pudieron cargar los campeonatos."));
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [competitionsRetryToken]);

  // Si no hay campeonato en la URL (primera visita), selecciona el primero.
  useEffect(() => {
    if (!competitions || competitions.length === 0 || compId) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set("comp", String(competitions[0].id));
    router.replace(`/programa?${params.toString()}`, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [competitions, compId]);

  const selected = competitions?.find((c) => c.id === compId) ?? null;

  // Nadadores del campeonato (para el multiselect y el filtro de cronograma).
  // Si no hay campeonato seleccionado el efecto no hace nada; los consumidores
  // de `swimmers` solo se montan cuando sí hay uno (ver render más abajo).
  useEffect(() => {
    if (!compId) return;
    let cancelled = false;
    api
      .get<CompetitionSwimmersResponse>(`/competitions/${compId}/swimmers`)
      .then((data) => {
        if (!cancelled) setSwimmers(data.items);
      })
      .catch(() => {
        if (!cancelled) setSwimmers([]);
      });
    return () => {
      cancelled = true;
    };
  }, [compId]);

  // Nadadores seguidos por el usuario en este campeonato.
  useEffect(() => {
    if (!compId || !user) return;
    const token = getToken();
    if (!token) return;
    let cancelled = false;
    api
      .get<WatchResponse>(`/competitions/${compId}/watch`, token)
      .then((data) => {
        if (!cancelled) setWatchNames(data.names);
      })
      .catch(() => {
        if (!cancelled) setWatchNames([]);
      });
    return () => {
      cancelled = true;
    };
  }, [compId, user]);

  function handleSelectCompetition(id: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("comp", String(id));
    params.delete("club");
    params.delete("swimmer");
    router.replace(`/programa?${params.toString()}`, { scroll: false });
  }

  function handleUploaded(result: CompetitionUploadResponse) {
    setCompetitionsRetryToken((t) => t + 1);
    const params = new URLSearchParams(searchParams.toString());
    params.set("comp", String(result.competition_id));
    params.delete("club");
    params.delete("swimmer");
    router.replace(`/programa?${params.toString()}`, { scroll: false });
  }

  function handleDeleted() {
    setCompetitionsRetryToken((t) => t + 1);
    const params = new URLSearchParams(searchParams.toString());
    params.delete("comp");
    params.delete("club");
    params.delete("swimmer");
    router.replace(`/programa?${params.toString()}`, { scroll: false });
  }

  if (competitionsError) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-destructive/40 p-10 text-center">
        <p className="text-sm text-destructive">{competitionsError}</p>
        <Button variant="outline" size="sm" onClick={() => setCompetitionsRetryToken((t) => t + 1)}>
          Reintentar
        </Button>
      </div>
    );
  }

  if (!competitions) {
    return <ProgramaSkeleton />;
  }

  if (competitions.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <ProgramaEmptyState />
        {user?.role === "admin" && (
          <AdminPanel selected={null} onUploaded={handleUploaded} onDeleted={handleDeleted} />
        )}
      </div>
    );
  }

  // Gateado por `user`: si se cierra sesión, no deben quedar marcadores 🔔
  // de una lista de seguidos que ya no aplica a la sesión actual.
  const watchedSet = user ? new Set(watchNames) : new Set<string>();

  return (
    <div className="flex flex-col gap-8">
      <CompetitionSelector
        competitions={competitions}
        selected={selected}
        onChange={handleSelectCompetition}
      />

      {selected && compId && (
        <>
          {user ? (
            watchNames.length > 0 ? (
              <AlertsSection compId={compId} loggedIn onLoginClick={() => setAuthOpen(true)} />
            ) : (
              <p className="text-sm text-muted-foreground">
                Sigue nadadores abajo para ver tus alertas de próximas pruebas.
              </p>
            )
          ) : (
            <AlertsSection
              compId={compId}
              loggedIn={false}
              onLoginClick={() => setAuthOpen(true)}
            />
          )}

          <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
            {user && (
              <WatchSwimmers
                compId={compId}
                swimmers={swimmers}
                watchNames={watchNames}
                onSaved={setWatchNames}
              />
            )}
            <ScheduleView compId={compId} swimmers={swimmers} watchedNames={watchedSet} />
          </div>

          {user?.role === "admin" && (
            <AdminPanel selected={selected} onUploaded={handleUploaded} onDeleted={handleDeleted} />
          )}
        </>
      )}

      <AuthDialog open={authOpen} onOpenChange={setAuthOpen} />
    </div>
  );
}
