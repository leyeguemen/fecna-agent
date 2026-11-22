"""Torneo de cada marca, desde el "Historial Deportivo" de FECNA.

El ranking solo trae la fecha; el historial por nadador sí trae el nombre del torneo, pero exige
una consulta por nadador y por prueba. Por eso solo se consulta para los nadadores seguidos o
vinculados a una cuenta, nunca para toda la base.
"""

import logging
import time
from datetime import date

from . import db as database
from .extractor import SiteBlockedError, TIMEOUT, _check, build_session
from .normalizer import time_to_ms

logger = logging.getLogger(__name__)

BASE = "https://ecoapplet.co/fecna/reportes/"
DEFAULT_DELAY = 0.6


def fetch_tournaments(swimmer_id: str, event_ids: list[str], session=None, delay: float = DEFAULT_DELAY,
                      inicio: str = "2000-01-01", fin: str | None = None) -> list[dict]:
    """Marcas con su torneo y puntos: [{event_id, pool, time_ms, date, tournament, points}]."""
    session = session or build_session()
    _check(session.get(BASE + "historial", timeout=TIMEOUT))
    _check(session.post(BASE + "historialFilter", timeout=TIMEOUT, data={
        "inicio": inicio, "fin": fin or date.today().isoformat(),
        "nadador": swimmer_id, "anual": "0", "prueba": "",
    }))
    out = []
    for event_id in event_ids:
        if delay:
            time.sleep(delay)
        resp = session.get(f"{BASE}{event_id}/getHistorial", timeout=TIMEOUT)
        _check(resp)
        rows = resp.json()
        if not isinstance(rows, list):
            continue
        for r in rows:
            try:
                out.append({
                    "event_id": str(r["prueba_id"]), "pool": r["piscina"],
                    "time_ms": time_to_ms(r["tiempo"]), "date": r["fecha_torneo"],
                    "tournament": (r.get("torneo") or "").strip(),
                    "points": int(r["puntos"]) if str(r.get("puntos") or "").isdigit() else None,
                })
            except (KeyError, ValueError):
                continue
    return [m for m in out if m["tournament"]]


def _open(source):
    """source: una conexión (se usa y no se cierra) o una función que abre una nueva (se cierra al terminar)."""
    # (sqlite3.Connection también es «callable», por eso se distingue por tener execute)
    return (source, False) if hasattr(source, "execute") else (source(), True)


def _close(conn, owned: bool) -> None:
    if owned:
        try:
            conn.close()
        except Exception:
            pass


def enrich_swimmer(source, swimmer_id: str, delay: float = DEFAULT_DELAY) -> int:
    """Trae el historial completo de un nadador desde FECNA: completa el torneo de las marcas del ranking
    y guarda las demás en swimmer_mark. Devuelve cuántas marcas nuevas guardó.

    source: conexión o función que abre una. Con función, la base solo se abre para leer y para escribir:
    pedir 17 pruebas a FECNA tarda de 10 s a 1 min y Supabase cierra las conexiones inactivas.
    Nunca lanza: si FECNA falla, el nadador simplemente conserva lo que ya tenía."""
    conn = None
    owned = False
    try:
        conn, owned = _open(source)
        names = database.event_names(conn)
        _close(conn, owned)  # no mantener la conexión abierta durante la espera a FECNA
        if not names:
            return 0
        marks = fetch_tournaments(swimmer_id, sorted(names), delay=delay)  # todas las pruebas, no solo las del ranking
        conn, owned = _open(source)
        database.set_tournaments(conn, swimmer_id, marks)
        return database.save_history(conn, swimmer_id, marks, names)
    except SiteBlockedError:
        raise
    except Exception as exc:
        logger.warning("No se pudo obtener el historial de %s: %s", swimmer_id, exc)
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass
        return 0
    finally:
        if conn is not None:
            _close(conn, owned)


def enrich_tracked(source, delay: float = DEFAULT_DELAY) -> tuple[int, int]:
    """Actualiza los nadadores seguidos/vinculados. Devuelve (nadadores, marcas nuevas guardadas)."""
    conn, owned = _open(source)
    try:
        ids = database.tracked_swimmer_ids(conn)
    finally:
        _close(conn, owned)
    total = 0
    for sid in ids:
        total += enrich_swimmer(source, sid, delay)
    return len(ids), total
