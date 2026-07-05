export function ProgramaEmptyState() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border/60 p-10 text-center">
      <span className="text-2xl" aria-hidden="true">
        📋
      </span>
      <p className="font-medium">Aún no hay programas cargados.</p>
      <p className="text-sm text-muted-foreground">
        Cuando se cargue un programa de campeonato, aparecerá aquí.
      </p>
    </div>
  );
}
