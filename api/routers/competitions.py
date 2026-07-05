"""Endpoints de programas de campeonato.

Público (lee `app_conn`): listado, cronograma, clubes y nadadores del programa.
Usuario (Bearer): nadadores seguidos y "mis alertas", por usuario.
Admin: cargar (PDF) y borrar un programa.

La carga cruza el PDF con la base de LECTURA (`read_conn`: `event_index` /
`list_swimmers`) pero guarda el resultado en la base de ESCRITURA (`app_conn`).
"""

import io

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel

from api import security
from api.deps import app_conn, read_conn
from fecna_agent import db, programa
from fecna_agent.times import ms_to_time

router = APIRouter(prefix="/competitions", tags=["competitions"])


def _time_display(ms: int | None) -> str | None:
    return ms_to_time(ms)[3:] if ms else None


def _entry_item(r) -> dict:
    return {
        "date": r["session_date"],
        "session_no": r["session_no"],
        "start_time": r["start_time"],
        "event_number": r["event_number"],
        "event_label": r["event_label"],
        "category": r["category"],
        "heat": r["heat"],
        "lane": r["lane"],
        "swimmer_name": r["swimmer_name"],
        "club_code": r["club_code"],
        "seed": _time_display(r["seed_ms"]),
        "seed_ms": r["seed_ms"],
        "swimmer_id": r["swimmer_id"],
    }


class WatchBody(BaseModel):
    names: list[str]


# --- Público -------------------------------------------------------------------
@router.get("")
def list_competitions():
    conn = app_conn()
    try:
        rows = db.list_competitions(conn)
    finally:
        conn.close()
    return {
        "items": [
            {
                "id": r["id"],
                "name": r["name"],
                "pool_type": r["pool_type"],
                "loaded_at": r["loaded_at"],
                "entradas": r["entradas"],
            }
            for r in rows
        ]
    }


@router.get("/{comp_id}/schedule")
def get_schedule(comp_id: int, club: str | None = None, swimmer: str | None = None):
    conn = app_conn()
    try:
        rows = db.competition_schedule(conn, comp_id, club, swimmer)
    finally:
        conn.close()
    return {"items": [_entry_item(r) for r in rows]}


@router.get("/{comp_id}/clubs")
def get_clubs(comp_id: int):
    conn = app_conn()
    try:
        clubs = db.competition_clubs(conn, comp_id)
    finally:
        conn.close()
    return {"items": clubs}


@router.get("/{comp_id}/swimmers")
def get_swimmers(comp_id: int):
    conn = app_conn()
    try:
        rows = db.competition_swimmers(conn, comp_id)
    finally:
        conn.close()
    return {"items": [{"swimmer_name": n, "club_code": c} for n, c in rows]}


# --- Usuario (Bearer) ------------------------------------------------------------
@router.get("/{comp_id}/watch")
def get_watch(comp_id: int, user: dict = Depends(security.current_user)):
    conn = app_conn()
    try:
        names = db.list_watched(conn, comp_id, user_id=int(user["id"]))
    finally:
        conn.close()
    return {"names": names}


@router.put("/{comp_id}/watch")
def put_watch(comp_id: int, body: WatchBody, user: dict = Depends(security.current_user)):
    conn = app_conn()
    try:
        db.set_watched(conn, comp_id, body.names, user_id=int(user["id"]))
        names = db.list_watched(conn, comp_id, user_id=int(user["id"]))
    finally:
        conn.close()
    return {"names": names}


@router.get("/{comp_id}/alerts")
def get_alerts(comp_id: int, user: dict = Depends(security.current_user)):
    conn = app_conn()
    try:
        rows = db.watched_schedule(conn, comp_id, user_id=int(user["id"]))
    finally:
        conn.close()
    return {"items": [_entry_item(r) for r in rows]}


# --- Admin -----------------------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
def upload_competition(
    file: UploadFile = File(...), admin: dict = Depends(security.require_admin)
):
    data = file.file.read()
    try:
        competition, entries = programa.parse_pdf(io.BytesIO(data))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo leer el PDF: {exc}",
        ) from exc
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se reconocieron inscripciones en el PDF. "
            "¿Es un programa con texto (no escaneado)?",
        )
    if not competition.get("name"):
        competition["name"] = file.filename or "Campeonato sin título"

    read = read_conn()
    try:
        programa.map_event_ids(entries, db.event_index(read))
        stats = programa.match_swimmers(entries, db.list_swimmers(read))
    finally:
        read.close()

    conn = app_conn()
    try:
        result = db.save_competition(conn, competition, entries)
    finally:
        conn.close()

    return {
        "competition_id": result["competition_id"],
        "status": result["status"],
        "entradas": stats["total"],
        "cruzados": stats["matched"],
    }


@router.delete("/{comp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competition(comp_id: int, admin: dict = Depends(security.require_admin)):
    conn = app_conn()
    try:
        db.delete_competition(conn, comp_id)
    finally:
        conn.close()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
