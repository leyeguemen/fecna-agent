// Fechas «AAAA-MM-DD» del programa (sin zona horaria) en texto corto en español.

const DIAS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

function parse(iso?: string | null): Date | null {
  const m = iso ? /^(\d{4})-(\d{2})-(\d{2})/.exec(iso) : null;
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}

/** «2026-11-29» → «sáb 29 nov». Si no es una fecha, la devuelve igual. */
export function dayLabel(iso?: string | null): string {
  const d = parse(iso);
  return d ? `${DIAS[d.getDay()]} ${d.getDate()} ${MESES[d.getMonth()]}` : (iso ?? '');
}

/** «2026-11-29» → { day: 'sáb 29 nov', left: 'En 4 días' } respecto a hoy. */
export function when(iso?: string | null): { day: string; left: string } | null {
  const d = parse(iso);
  if (!d) return null;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const n = Math.round((d.getTime() - today.getTime()) / 86_400_000);
  return { day: dayLabel(iso), left: n <= 0 ? 'Hoy' : n === 1 ? 'Mañana' : `En ${n} días` };
}
