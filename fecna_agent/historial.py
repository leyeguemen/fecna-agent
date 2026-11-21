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
    """Marcas con su torneo: [{event_id, pool, time_ms, date, tournament}]."""
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
                })
            except (KeyError, ValueError):
                continue
    return [m for m in out if m["tournament"]]


def enrich_swimmer(conn, swimmer_id: str, delay: float = DEFAULT_DELAY) -> int:
    """Completa el torneo de las marcas de un nadador. Devuelve cuántas actualizó.
    Nunca lanza: si FECNA falla, las marcas simplemente quedan sin torneo."""
    try:
        events = database.swimmer_event_ids(conn, swimmer_id)
        if not events:
            return 0
        return database.set_tournaments(conn, swimmer_id, fetch_tournaments(swimmer_id, events, delay=delay))
    except SiteBlockedError:
        raise
    except Exception as exc:
        logger.warning("No se pudo obtener el torneo de %s: %s", swimmer_id, exc)
        try:
            conn.rollback()
        except Exception:
            pass
        return 0


def enrich_tracked(conn, delay: float = DEFAULT_DELAY) -> tuple[int, int]:
    """Actualiza los nadadores seguidos/vinculados. Devuelve (nadadores, marcas actualizadas)."""
    ids = database.tracked_swimmer_ids(conn)
    total = 0
    for sid in ids:
        total += enrich_swimmer(conn, sid, delay)
    return len(ids), total
