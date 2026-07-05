/** Placeholder "pulse" mientras carga el selector de campeonatos (fallback
 * del `Suspense` que envuelve `ProgramaSection`, ver `app/programa/page.tsx`). */
export function ProgramaSkeleton() {
  return (
    <div className="flex flex-col gap-4" role="status" aria-label="Cargando programa">
      <div className="h-8 w-64 animate-pulse rounded-lg bg-muted" />
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-xl border border-border/60 p-3">
          <div className="h-4 w-20 shrink-0 animate-pulse rounded bg-muted" />
          <div className="h-4 flex-1 animate-pulse rounded bg-muted" />
          <div className="hidden h-4 w-24 animate-pulse rounded bg-muted sm:block" />
        </div>
      ))}
    </div>
  );
}
