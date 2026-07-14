import Link from "next/link";

/**
 * Encabezado de contenido al estilo AdminLTE: título a la izquierda y
 * breadcrumb a la derecha ("Inicio / Página"). En la página de inicio basta
 * con `<ContentHeader title="…" home />` para no duplicar el crumb.
 */
export function ContentHeader({
  title,
  crumb,
  home = false,
}: {
  title: string;
  /** Etiqueta del breadcrumb cuando difiere del título (p. ej. "Nadador"). */
  crumb?: string;
  home?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 print:hidden">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <nav aria-label="Ruta de navegación">
        <ol className="flex items-center gap-1.5 text-sm text-muted-foreground">
          {home ? (
            <li aria-current="page">Inicio</li>
          ) : (
            <>
              <li>
                <Link href="/" className="text-primary hover:underline">
                  Inicio
                </Link>
              </li>
              <li aria-hidden="true">/</li>
              <li aria-current="page">{crumb ?? title}</li>
            </>
          )}
        </ol>
      </nav>
    </div>
  );
}
