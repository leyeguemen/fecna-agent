import type { Ref } from "react";

import type { SwimmerProfile, SwimmerTopEvent } from "@/lib/types";

const MEDALS: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };
const GENDER_LABELS: Record<string, string> = { M: "Masculino", F: "Femenino" };
const TIERS = [3, 5, 10, 20, 50];

export interface FichaCustomization {
  photo: string | null;
  logo: string | null;
  championship: string;
  venue: string;
}

function shortEvent(name: string): string {
  return name.split("/")[0]?.trim() || name;
}

function rankTier(rank: number): number {
  return TIERS.find((tier) => rank <= tier) ?? Math.ceil(rank / 10) * 10;
}

function prettyTime(milliseconds: number): string {
  const centiseconds = Math.floor((milliseconds % 1000) / 10);
  const totalSeconds = Math.floor(milliseconds / 1000);
  const seconds = totalSeconds % 60;
  const totalMinutes = Math.floor(totalSeconds / 60);
  const minutes = totalMinutes % 60;
  const hours = Math.floor(totalMinutes / 60);
  const fraction = `${seconds.toString().padStart(2, "0")}.${centiseconds.toString().padStart(2, "0")}`;
  if (hours) return `${hours}:${minutes.toString().padStart(2, "0")}:${fraction}`;
  if (minutes) return `${minutes}:${fraction}`;
  return `${seconds}.${centiseconds.toString().padStart(2, "0")}`;
}

function position(rank: number, total: number) {
  return (
    <>
      {MEDALS[rank] && <span aria-hidden="true">{MEDALS[rank]} </span>}
      {rank}.º <span className="ficha-of">de {total}</span>
    </>
  );
}

function EventChip({ event }: { event: SwimmerTopEvent }) {
  return (
    <div className="ficha-highlight-chip">
      <strong>{shortEvent(event.event_name)}</strong>
      <span>{prettyTime(event.best_ms)}</span>
      <span className="ficha-highlight-position">
        {event.league_rank}.º de {event.league_total}
      </span>
    </div>
  );
}

export function FichaInfografia({
  profile,
  customization,
  cardRef,
}: {
  profile: SwimmerProfile;
  customization: FichaCustomization;
  cardRef?: Ref<HTMLDivElement>;
}) {
  const parts = profile.swimmer_name.trim().split(/\s+/);
  const firstName = parts.shift() ?? profile.swimmer_name;
  const lastNames = parts.join(" ");
  const bestNational = profile.top_events.reduce<SwimmerTopEvent | null>(
    (best, event) => (!best || event.national_rank < best.national_rank ? event : best),
    null,
  );
  const leagueGold = profile.top_events.filter((event) => event.league_rank === 1);
  const leagueSilver = profile.top_events.filter((event) => event.league_rank === 2);
  const leagueBronze = profile.top_events.filter((event) => event.league_rank === 3);
  const leaguePodium = leagueGold.length ? leagueGold : leagueSilver.length ? leagueSilver : leagueBronze;
  const leagueRank = leaguePodium[0]?.league_rank;
  const leagueTitle = leagueRank === 1 ? "CAMPEÓN" : leagueRank === 2 ? "SUBCAMPEÓN" : "TERCERO";

  return (
    <article ref={cardRef} className="ficha-card" aria-label={`Ficha de ${profile.swimmer_name}`}>
      <header className="ficha-hero">
        {customization.photo && (
          // eslint-disable-next-line @next/next/no-img-element -- vista previa de un archivo local del usuario
          <img className="ficha-photo" src={customization.photo} alt="Foto del nadador" />
        )}
        <div className="ficha-hero-main">
          {customization.logo && (
            // eslint-disable-next-line @next/next/no-img-element -- vista previa de un archivo local del usuario
            <img className="ficha-logo" src={customization.logo} alt="Logo del club" />
          )}
          <div className="ficha-name">
            <span>{firstName}</span>
            {lastNames && <strong>{lastNames}</strong>}
          </div>
          <div className="ficha-category">
            {profile.age} AÑOS <span>·</span> {GENDER_LABELS[profile.gender] ?? profile.gender}
          </div>
          <div className="ficha-club">
            {profile.club} <span>·</span> LIGA {profile.league}
          </div>
          {(customization.championship || customization.venue) && (
            <div className="ficha-championship">
              <strong>{customization.championship}</strong>
              <span>{customization.venue}</span>
            </div>
          )}
        </div>
      </header>

      <div className="ficha-highlights">
        {bestNational && (
          <section className="ficha-highlight ficha-highlight-national">
            <span className="ficha-highlight-medal" aria-hidden="true">🥇</span>
            <h2>
              {bestNational.national_rank === 1
                ? "CAMPEÓN DE COLOMBIA"
                : `TOP ${rankTier(bestNational.national_rank)} DE COLOMBIA`}
            </h2>
            <div className="ficha-highlight-detail">
              <strong>{shortEvent(bestNational.event_name)}</strong>
              <span>{prettyTime(bestNational.best_ms)}</span>
              <span>{bestNational.national_rank}.º de {bestNational.national_total} nacional</span>
            </div>
          </section>
        )}

        {leaguePodium.length > 0 && (
          <section className="ficha-highlight ficha-highlight-league">
            <h2>{MEDALS[leagueRank ?? 0]} {leagueTitle} LIGA {profile.league}</h2>
            <div className="ficha-highlight-chips">
              {leaguePodium.map((event) => (
                <EventChip key={`${event.event_id}-${event.pool}`} event={event} />
              ))}
            </div>
          </section>
        )}
      </div>

      <div className="ficha-table-wrap">
        <table className="ficha-table">
          <thead>
            <tr>
              <th>Prueba</th>
              <th>Mejor marca</th>
              <th>🏆 Ranking liga</th>
              <th>🇨🇴 Ranking Colombia</th>
            </tr>
          </thead>
          <tbody>
            {profile.top_events.map((event) => (
              <tr key={`${event.event_id}-${event.pool}`}>
                <td className="ficha-event">
                  {shortEvent(event.event_name)} <span>{event.pool}</span>
                </td>
                <td className="ficha-time">{prettyTime(event.best_ms)}</td>
                <td>{position(event.league_rank, event.league_total)}</td>
                <td>{position(event.national_rank, event.national_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <blockquote className="ficha-quote">
        “El esfuerzo de cada entrenamiento se refleja en los resultados. <strong>{profile.swimmer_name}</strong>{" "}
        continúa posicionándose entre los mejores nadadores de Colombia en la categoría {profile.age} años,
        llevando con orgullo los colores de {profile.club}.”
      </blockquote>
      <footer className="ficha-reference">
        Categoría calculada al año {profile.reference_year} · Nacimiento: {profile.birth_date ?? "—"} ·
        Puesto por género y categoría · Fuente: ranking FECNA
      </footer>
    </article>
  );
}
