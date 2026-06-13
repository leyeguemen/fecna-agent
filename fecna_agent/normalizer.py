"""Normaliza los registros JSON crudos de getRanking al modelo de datos local."""

import logging
from datetime import datetime, timezone

from .times import time_to_ms

logger = logging.getLogger(__name__)

SOURCE = "fecna_ranking"


def normalize_rows(raw_rows: list[dict], fetched_at: str | None = None) -> list[dict]:
    """Convierte registros crudos en filas listas para insertar.

    Los registros inválidos (tiempo mal formado, campos faltantes) se
    descartan con un log de advertencia en vez de abortar la carga.
    fetched_at permite estampar toda una corrida de sincronización con el
    mismo timestamp para luego identificar qué resultados entraron en ella.
    """
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    rows = []
    for raw in raw_rows:
        try:
            rows.append(normalize_row(raw, fetched_at))
        except (KeyError, ValueError) as exc:
            logger.warning("Registro descartado (%s): %s", exc, raw)
    return rows


def normalize_row(raw: dict, fetched_at: str) -> dict:
    return {
        "source": SOURCE,
        "ranking_position": _to_int(raw.get("contador")),
        "swimmer_id": str(raw["identificacion"]),
        "swimmer_name": raw.get("nada") or f"{raw.get('nombre', '')} {raw.get('apellido', '')}".strip(),
        "first_name": raw.get("nombre"),
        "last_name": raw.get("apellido"),
        "gender": (raw.get("genero") or "").upper() or None,
        "birth_date": raw.get("fecha_nac"),
        "birth_year_month": raw.get("edad"),
        "event_id": str(raw["prueba_id"]),
        "event_name": raw.get("prueba", ""),
        "pool_type": raw["piscina"],
        "time_raw": raw["tiempo"],
        "time_ms": time_to_ms(raw["tiempo"]),
        "points": _to_int(raw.get("puntos")),
        "result_date": raw.get("fecha_tor"),
        "league": raw.get("nombre_liga"),
        "club": raw.get("nombre_club"),
        "fetched_at": fetched_at,
    }


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
