"""Endpoints de lectura pública de nadadores: búsqueda, ficha e historial."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, Response

from api import security
from api.deps import read_conn
from api.routers.auth import limiter
from fecna_agent import db, ficha, ficha_imagen, programa
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


@router.get("/compare", dependencies=[Depends(security.require_permission("comparar"))])
def compare(a: str, b: str, event_id: str, pool: Literal["LC", "SC"] | None = None):
    """Compara las mejores marcas de dos nadadores en una prueba."""
    conn = read_conn()
    try:
        res = db.compare_swimmers(conn, a, b, event_id, pool)
    finally:
        conn.close()

    def side(r):
        return None if r is None else {
            "swimmer_id": r["swimmer_id"], "swimmer_name": r["swimmer_name"],
            "time": _time_display(r["time_ms"]), "time_ms": r["time_ms"],
            "club": r["club"], "date": r["result_date"],
        }

    diff = res["diff_ms"]
    return {"a": side(res["a"]), "b": side(res["b"]),
            "diff": _time_display(diff) if diff is not None else None, "diff_ms": diff}


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
        # Solo el año: la fecha exacta es el secreto con el que se verifica el vínculo de cuenta.
        "birth_year": (str(data["birth_date"])[:4] if data["birth_date"] else None),
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
            "points": row["points"],
            "tournament": row["tournament"],
        }
        for row in rows
    ]
    return {"items": items}


MAX_PHOTO_BYTES = 8 * 1024 * 1024


@router.post("/{swimmer_id}/ficha-redes", dependencies=[Depends(security.require_permission("ficha_redes"))])
@limiter.limit("20/minute")
def get_swimmer_ficha_redes(
    request: Request,
    swimmer_id: str,
    tournament: str | None = Form(default=None, max_length=200),
    photo: UploadFile | None = File(default=None),
):
    """Imagen PNG 9:16 para compartir en redes. La foto es opcional y no se guarda."""
    photo_bytes = None
    if photo is not None:
        photo_bytes = photo.file.read(MAX_PHOTO_BYTES + 1)
        if len(photo_bytes) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=413, detail="La foto pesa demasiado (máximo 8 MB).")
    conn = read_conn()
    try:
        profile = db.swimmer_summary(conn, swimmer_id)
        names = conn.execute(
            "SELECT first_name, last_name, gender FROM ranking_results WHERE swimmer_id = ? "
            "ORDER BY result_date DESC LIMIT 1", (swimmer_id,)).fetchone()
        ranks_rows = db.swimmer_event_ranks(conn, swimmer_id)
        rows = [dict(r) for r in db.history(conn, swimmer_id)]
    finally:
        conn.close()
    if profile is None or not ranks_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nadador no encontrado.")
    ranks = {(r["event_id"], r["pool_type"]): (r["national_rank"], r["best_ms"]) for r in ranks_rows}
    marks = ficha_imagen.select_marks(rows, ranks, tournament or None)
    if not marks:
        raise HTTPException(status_code=404, detail="Sin marcas para esa selección.")
    profile = {**profile, "age": ranks_rows[0]["age"],
               "first_name": names["first_name"] if names else None,
               "last_name": names["last_name"] if names else None}
    try:
        png = ficha_imagen.render_png(profile, marks, tournament or None, photo_bytes)
    except (ValueError, OSError):
        raise HTTPException(status_code=422, detail="No pudimos leer esa foto. Prueba con otra imagen (JPG o PNG).")
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/{swimmer_id}/ficha", response_class=HTMLResponse)
def get_swimmer_ficha(swimmer_id: str):
    """Ficha visual (HTML auto-contenido) para descargar. Sin fecha de nacimiento exacta."""
    conn = read_conn()
    try:
        data = db.swimmer_profile(conn, swimmer_id)
    finally:
        conn.close()
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nadador no encontrado.")
    data = dict(data)
    data["birth_date"] = str(data["birth_date"])[:4] if data.get("birth_date") else None
    return HTMLResponse(ficha.render_html(data))
