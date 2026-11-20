"""Endpoints de lectura pública: catálogos y rankings (/catalogs, /rankings)."""

from fastapi import APIRouter, Query

from api.deps import read_conn
from fecna_agent import categories, db
from fecna_agent.times import ms_to_time

router = APIRouter(tags=["rankings"])


def _time_display(ms: int) -> str:
    """Formato corto 'MM:SS.cc' (se descartan las horas), igual convención
    que pages/programa.py y pages/alertas.py: ms_to_time(ms)[3:]."""
    return ms_to_time(ms)[3:]


@router.get("/catalogs")
def get_catalogs():
    conn = read_conn()
    try:
        pruebas = db.get_catalog(conn, "prueba")
        categorias = db.get_catalog(conn, "categoria_M")
    finally:
        conn.close()
    return {
        "pruebas": [{"id": code, "nombre": label} for code, label in pruebas],
        "categorias": [{"id": code, "nombre": label} for code, label in categorias],
        "piscinas": ["LC", "SC"],
        "generos": ["M", "F"],
    }


@router.get("/rankings")
def get_rankings(
    event_id: str,
    pool: str | None = None,
    gender: str | None = None,
    category: str | None = None,
    limit: int = Query(25, ge=1, le=100),
):
    age_range = categories.age_range(category) if category else None
    conn = read_conn()
    try:
        rows = db.ranking(
            conn, event_id, pool_type=pool, gender=gender, limit=limit,
            age_range=age_range,
        )
    finally:
        conn.close()
    items = [
        {
            "pos": pos,
            "swimmer_id": row["swimmer_id"],
            "swimmer_name": row["swimmer_name"],
            "time": _time_display(row["time_ms"]),
            "time_ms": row["time_ms"],
            "club": row["club"],
            "league": row["league"],
            "date": row["result_date"],
        }
        for pos, row in enumerate(rows, start=1)
    ]
    return {"event_id": event_id, "total": len(items), "items": items}
