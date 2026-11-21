"""Sincronización masiva: todas las pruebas × piscinas × géneros en una corrida.

Cada corrida queda registrada en sync_log con un timestamp único (run_at) que
también se estampa en fetched_at de cada resultado nuevo. Así, al terminar un
campeonato se puede re-sincronizar y verificar exactamente qué entró nuevo.

La extracción es idempotente: los resultados ya conocidos se ignoran por la
restricción UNIQUE de la tabla.
"""

import logging
import time
from datetime import date, timedelta, datetime, timezone

from . import db as database
from . import extractor, normalizer

logger = logging.getLogger(__name__)

DEFAULT_DELAY = 0.6  # cortesía con el servidor entre peticiones

# Cortacircuito: si el sitio falla seguido, insistir solo empeora el bloqueo
MAX_CONSECUTIVE_ERRORS = 3


BASE_START = "2024-01-01"  # primera fecha con datos en la base
DEFAULT_MARGIN_DAYS = 30


def incremental_start(conn, margin_days: int = DEFAULT_MARGIN_DAYS, today: date | None = None) -> str:
    """Fecha de inicio para una sincronización incremental.

    Es la marca más reciente guardada menos un margen: FECNA a veces publica resultados con
    retraso o con fecha anterior, y las inserciones repetidas se ignoran (restricción UNIQUE),
    así que solapar es seguro. Si la base está vacía, parte de BASE_START.
    """
    row = conn.execute("SELECT MAX(result_date) FROM ranking_results").fetchone()
    latest = row[0] if row else None
    if not latest:
        return BASE_START
    try:
        start = date.fromisoformat(str(latest)[:10]) - timedelta(days=margin_days)
    except ValueError:
        return BASE_START
    return min(max(start, date.fromisoformat(BASE_START)), today or date.today()).isoformat()


def sync_all(
    conn,
    inicio: str = "2024-01-01",
    fin: str | None = None,
    events: list[tuple[str, str]] | None = None,
    pools: tuple[str, ...] = ("LC", "SC"),
    genders: tuple[str, ...] = ("M", "F"),
    categoria: str | list[str] = "",
    delay: float = DEFAULT_DELAY,
    progress=None,
) -> dict:
    """Recorre todas las combinaciones y guarda los resultados.

    categoria vacía = todas las categorías del género (el servidor exige al
    menos una; se envían todas juntas porque categoria[] es select múltiple).
    progress: callback opcional (hecho, total, detalle) para CLI/Streamlit.
    Devuelve stats: run_at, combos, received, inserted, errors, details.
    """
    fin = fin or date.today().isoformat()
    events = events or database.get_catalog(conn, "prueba")
    if not events:
        raise RuntimeError("No hay catálogo de pruebas: ejecuta 'catalog' primero.")

    categories_by_gender = {}
    for gender in genders:
        if categoria:
            categories_by_gender[gender] = categoria
        else:
            cats = database.get_catalog(conn, f"categoria_{gender}")
            if not cats:
                raise RuntimeError(
                    f"No hay catálogo de categorías para {gender}: "
                    "re-ejecuta 'catalog' (el servidor exige al menos una categoría)."
                )
            categories_by_gender[gender] = [code for code, _ in cats]

    run_at = datetime.now(timezone.utc).isoformat()
    session = extractor.build_session()
    combos = [(e, p, g) for e in events for p in pools for g in genders]
    stats = {
        "run_at": run_at, "inicio": inicio, "fin": fin,
        "combos": len(combos), "received": 0, "inserted": 0, "errors": 0,
        "aborted": "", "details": [],
    }

    consecutive_errors = 0
    for done, ((event_id, event_name), pool, gender) in enumerate(combos, 1):
        try:
            raw = extractor.fetch_ranking(
                inicio=inicio, fin=fin, genero=gender,
                categoria=categories_by_gender[gender],
                prueba=event_id, piscina=pool, session=session,
            )
            rows = normalizer.normalize_rows(raw, fetched_at=run_at)
            inserted = database.insert_results(conn, rows)
        except Exception as exc:
            failure = exc
            try:
                conn.rollback()  # una transacción abortada (p. ej. deadlock) no debe arrastrar a las demás
            except Exception:
                pass
            stats["errors"] += 1
            consecutive_errors += 1
            logger.warning("Fallo en %s %s %s: %s", event_name, pool, gender, exc)
            detail = (event_name, pool, gender, 0, 0, str(exc))
        else:
            failure = None
            consecutive_errors = 0
            stats["received"] += len(raw)
            stats["inserted"] += inserted
            detail = (event_name, pool, gender, len(raw), inserted, "")
        stats["details"].append(detail)
        if progress:
            progress(done, len(combos), detail)

        blocked = isinstance(failure, extractor.SiteBlockedError)
        if blocked or consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            stats["aborted"] = (
                str(failure) if blocked else
                f"{consecutive_errors} errores consecutivos; el sitio parece "
                "caído o está bloqueando: se detiene la corrida para no insistir."
            )
            logger.error("Sincronización abortada: %s", stats["aborted"])
            break
        if delay:
            time.sleep(delay)

    database.log_sync(conn, stats)
    return stats
