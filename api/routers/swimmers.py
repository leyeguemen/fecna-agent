"""Endpoints de lectura pública de nadadores: búsqueda, ficha e historial."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from api.deps import read_conn
from fecna_agent import db, programa
from fecna_agent.times import ms_to_time

router = APIRouter(prefix="/swimmers", tags=["swimmers"])


def _time_display(ms: int) -> str:
    return ms_to_time(ms)[3:]


# NOTA: "/search" se declara antes de "/{swimmer_id}" para que FastAPI la
# resuelva primero (si no, "search" se interpretaría como un swimmer_id).
@router.get("/search")
def search_swimmers(q: str = Query(..., min_length=3)):
    conn = read_conn()
    try:
        swimmers = db.list_swimmers_detailed(conn)
    finally:
        conn.close()
    needle = programa.normalize(q)
    items = [
        {"swimmer_id": sid, "swimmer_name": name, "club": club, "league": league}
        for sid, name, club, league in swimmers
        if needle in programa.normalize(name)
    ][:20]
    return {"items": items}


@router.get("/options")
def swimmer_options(league: str | None = None):
    """Opciones para el selector de la ficha, con filtro opcional por liga."""
    conn = read_conn()
    try:
        swimmers = db.list_swimmers_detailed(conn, league=league)
        leagues = db.list_leagues(conn)
    finally:
        conn.close()
    return {
        "leagues": leagues,
        "items": [
            {"swimmer_id": sid, "swimmer_name": name, "club": club or "", "league": item_league or ""}
            for sid, name, club, item_league in swimmers
        ],
    }


@router.get("/{swimmer_id}")
def get_swimmer_profile(
    swimmer_id: str,
    pool: Literal["LC", "SC"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha inicial no puede ser posterior a la fecha final.",
        )
    conn = read_conn()
    try:
        data = db.swimmer_profile(
            conn,
            swimmer_id,
            pool_type=pool,
            date_from=date_from.isoformat() if date_from else None,
            date_to=date_to.isoformat() if date_to else None,
        )
    finally:
        conn.close()
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nadador no encontrado.",
        )
    return {
        "swimmer_id": data["swimmer_id"],
        "swimmer_name": data["swimmer_name"],
        "gender": data["gender"],
        "age": data["age"],
        "league": data["league"],
        "club": data["club"],
        "birth_date": data["birth_date"],
        "reference_year": data["reference_year"],
        "top_events": [
            {
                "event_id": r["event_id"],
                "event_name": r["event_name"],
                "pool": r["pool_type"],
                "best_ms": r["best_ms"],
                "best_time": _time_display(r["best_ms"]),
                "national_rank": r["national_rank"],
                "national_total": r["national_total"],
                "league_rank": r["league_rank"],
                "league_total": r["league_total"],
            }
            for r in data["top_events"]
        ],
    }


@router.get("/{swimmer_id}/history")
def get_swimmer_history(swimmer_id: str, event_id: str | None = None, pool: str | None = None):
    conn = read_conn()
    try:
        rows = db.history(conn, swimmer_id, event_id=event_id, pool_type=pool)
    finally:
        conn.close()
    items = [
        {
            "date": row["result_date"],
            "time": _time_display(row["time_ms"]),
            "time_ms": row["time_ms"],
            "event_id": row["event_id"],
            "event_name": row["event_name"],
            "pool": row["pool_type"],
        }
        for row in rows
    ]
    return {"items": items}
