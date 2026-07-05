/** Filas "pulse" mientras carga el ranking o los catálogos de filtros. */
export function RankingSkeleton() {
  return (
    <div className="flex flex-col gap-2" role="status" aria-label="Cargando ranking">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 rounded-xl border border-border/60 p-3"
        >
          <div className="h-4 w-6 shrink-0 animate-pulse rounded bg-muted" />
          <div className="h-4 w-14 shrink-0 animate-pulse rounded bg-muted" />
          <div className="h-4 flex-1 animate-pulse rounded bg-muted" />
          <div className="hidden h-4 w-24 animate-pulse rounded bg-muted sm:block" />
          <div className="hidden h-4 w-20 animate-pulse rounded bg-muted md:block" />
        </div>
      ))}
    </div>
  );
}
