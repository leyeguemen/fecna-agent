import Link from "next/link";

/**
 * Fila de título y breadcrumb con el markup de AdminLTE 4.
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
    <div className="row print:hidden">
      <div className="col-sm-6">
        <h3 className="mb-0">{title}</h3>
      </div>
      <div className="col-sm-6">
        <nav aria-label="Ruta de navegación">
          <ol className="breadcrumb float-sm-end">
            {home ? (
              <li className="breadcrumb-item active" aria-current="page">
                Inicio
              </li>
            ) : (
              <>
                <li className="breadcrumb-item">
                  <Link href="/">Inicio</Link>
                </li>
                <li className="breadcrumb-item active" aria-current="page">
                  {crumb ?? title}
                </li>
              </>
            )}
          </ol>
        </nav>
      </div>
    </div>
  );
}
