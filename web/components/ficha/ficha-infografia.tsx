import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SwimmerProfile, SwimmerTopEvent } from "@/lib/types";

const MEDALS: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };

const GENDER_LABELS: Record<string, string> = {
  M: "Masculino",
  F: "Femenino",
};

const POOL_LABELS: Record<string, string> = {
  LC: "Piscina larga (LC)",
  SC: "Piscina corta (SC)",
};

const RANK_BADGE_STYLES: Record<number, string> = {
  1: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  2: "bg-slate-400/20 text-slate-600 dark:text-slate-300",
  3: "bg-orange-700/15 text-orange-700 dark:text-orange-400",
};

function ordinal(n: number): string {
  return `${n}º`;
}

function formatBirthDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  if (!year || !month || !day) return iso;
  return `${day}/${month}/${year}`;
}

/** La infografía compartible/imprimible: encabezado del nadador + grilla de
 * sus mejores pruebas con puesto nacional. Es la única sección visible al
 * imprimir (ver `print:` en las clases y los overrides en globals.css). */
export function FichaInfografia({ profile }: { profile: SwimmerProfile }) {
  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-border/60 bg-card p-6 ring-1 ring-foreground/5 sm:p-8 print:rounded-none print:border-0 print:p-0 print:ring-0">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          {profile.swimmer_name}
        </h1>
        <p className="text-muted-foreground">
          {profile.club} · {profile.league}
        </p>
        <p className="text-sm text-muted-foreground">
          {GENDER_LABELS[profile.gender] ?? profile.gender}
          {" · "}
          {profile.age} años
          <span className="text-xs"> (edad de referencia a {profile.reference_year})</span>
          {profile.birth_date && (
            <> · Nacimiento: {formatBirthDate(profile.birth_date)}</>
          )}
        </p>
      </header>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold tracking-tight text-muted-foreground uppercase">
          Mejores pruebas
        </h2>
        {profile.top_events.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Este nadador aún no tiene tiempos registrados.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 print:grid-cols-2 print:gap-2">
            {profile.top_events.map((event) => (
              <TopEventCard key={`${event.event_id}-${event.pool}`} event={event} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function TopEventCard({ event }: { event: SwimmerTopEvent }) {
  const medal = MEDALS[event.national_rank];
  const badgeStyle = RANK_BADGE_STYLES[event.national_rank] ?? "bg-muted text-muted-foreground";

  return (
    <Card size="sm" className="print:break-inside-avoid print:ring-1 print:ring-black/20">
      <CardHeader>
        <CardTitle className="flex items-start justify-between gap-2">
          <span>{event.event_name}</span>
        </CardTitle>
        <p className="text-xs text-muted-foreground">{POOL_LABELS[event.pool] ?? event.pool}</p>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <span className="font-mono text-2xl font-semibold tabular-nums">{event.best_time}</span>

        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium ${badgeStyle}`}
          >
            {medal && <span aria-hidden="true">{medal}</span>}
            {ordinal(event.national_rank)} de {event.national_total} (nacional)
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
            {ordinal(event.league_rank)} de {event.league_total} (liga)
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
