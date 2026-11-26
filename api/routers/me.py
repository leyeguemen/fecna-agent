"""Cuenta del usuario: nadador vinculado, nadadores seguidos, contraseña y borrado (/me/*)."""

import re
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from api import security
from api.deps import app_conn, read_conn
from api.routers.auth import limiter
from fecna_agent import db, historial
from fecna_agent.times import ms_to_time

router = APIRouter(prefix="/me", tags=["me"])

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class LinkBody(BaseModel):
    swimmer_id: str
    birth_date: str  # AAAA-MM-DD, se verifica contra la base


class PasswordBody(BaseModel):
    current: str
    new: str


def _uid(user: dict) -> int:
    return int(user["id"])


def _summary(swimmer_id: str | None) -> dict | None:
    if not swimmer_id:
        return None
    conn = read_conn()
    try:
        return db.swimmer_summary(conn, swimmer_id)
    finally:
        conn.close()


def _read_info(swimmer_id: str | None) -> tuple[dict | None, str | None]:
    """Resumen del nadador vinculado y fecha del resultado más reciente (para "Acerca de")."""
    conn = read_conn()
    try:
        summary = db.swimmer_summary(conn, swimmer_id) if swimmer_id else None
        data_until = conn.execute("SELECT MAX(result_date) FROM ranking_results").fetchone()[0]
    finally:
        conn.close()
    return summary, (str(data_until) if data_until else None)


@router.get("")
def my_profile(user: dict = Depends(security.active_user)):
    conn = app_conn()
    try:
        swimmer_id = db.get_user_swimmer_id(conn, _uid(user))
        following = db.list_following(conn, _uid(user))
    finally:
        conn.close()
    swimmer, data_until = _read_info(swimmer_id)
    return {"email": user["email"], "role": user["role"],
            "swimmer": swimmer, "following": following, "data_until": data_until}


# Campeonatos de mínimas que se prueban para el Inicio, en orden (el nadador cae en uno según su edad).
_HOME_MINIMAS = ("infantiles", "interligas")


def _home_minima(swimmer_id: str) -> dict | None:
    """La prueba en la que mejor cumple la mínima o, si no cumple ninguna, la más cercana que le falta.

    El margen es relativo a la mínima, para comparar pruebas cortas con largas (1 s en 50 m pesa más que en 800 m).
    """
    from api.routers.minimas import evaluate_swimmer
    from fecna_agent import minimas

    for tournament in _HOME_MINIMAS:
        ev = evaluate_swimmer(swimmer_id, tournament)
        if not ev or not ev["applicable"]:
            continue
        margin = lambda r: r["diff_ms"] / r["minima_ms"]  # noqa: E731
        met = [r for r in ev["rows"] if r["status"] == "cumple"]
        missing = [r for r in ev["rows"] if r["status"] == "falta"]
        row = max(met, key=margin) if met else min(missing, key=margin) if missing else None
        return {"tournament": tournament, "tournament_label": minimas.TOURNAMENTS[tournament],
                "category_label": ev["category_label"], "met": ev["met"], "total": ev["total"],
                "event": row["event"] if row else None, "status": row["status"] if row else None, "best": row["best"] if row else None,
                "minima": row["minima"] if row else None, "diff": row["diff"] if row else None,
                "best_ms": row["best_ms"] if row else None, "minima_ms": row["minima_ms"] if row else None}
    return None


def _home_competition(rows: list) -> dict | None:
    """El campeonato más próximo con inscripciones del usuario, y su primera prueba."""
    if not rows:
        return None
    from api.routers.competitions import _entry_item

    comp_id = rows[0]["competition_id"]
    mine = [r for r in rows if r["competition_id"] == comp_id]
    return {"id": comp_id, "name": rows[0]["competition_name"], "entries": len(mine),
            "swimmers": len({r["swimmer_name"] for r in mine}), "first": _entry_item(rows[0])}


@router.get("/home")
def home(user: dict = Depends(security.active_user)):
    """Resumen de la pantalla de Inicio. Cada bloque sale solo si el rol tiene el permiso de esa sección."""
    perms = set(user.get("permissions") or [])
    uid = _uid(user)
    conn = app_conn()
    try:
        swimmer_id = db.get_user_swimmer_id(conn, uid)
        following = len(db.list_following(conn, uid))
        torneos = "ver_torneos" in perms
        comps = len(db.list_competitions(conn)) if torneos else None
        upcoming = db.upcoming_entries(conn, uid, swimmer_id, date.today().isoformat()) if torneos else []
    finally:
        conn.close()

    swimmer = None
    if swimmer_id:
        rconn = read_conn()
        try:
            summary = db.swimmer_summary(rconn, swimmer_id)
            profile = db.swimmer_profile(rconn, swimmer_id) if summary and "ver_nadador" in perms else None
        finally:
            rconn.close()
        if summary:
            top = profile["top_events"][0] if profile and profile["top_events"] else None
            swimmer = {**summary,
                       "gender": profile["gender"] if profile else None,
                       "age": profile["age"] if profile else None,
                       "top_event": {"event_name": top["event_name"], "pool": top["pool_type"],
                                     "best_time": ms_to_time(top["best_ms"])[3:] if top["best_ms"] else None,
                                     "national_rank": top["national_rank"],
                                     "national_total": top["national_total"]} if top else None}

    return {"swimmer": swimmer,
            "minima": _home_minima(swimmer_id) if swimmer and "ver_minimas" in perms else None,
            "next_competition": _home_competition(upcoming),
            "following": following, "competitions": comps}


@router.put("/swimmer")
@limiter.limit("5/minute")  # frena la adivinanza de fechas de nacimiento
def link_swimmer(request: Request, body: LinkBody, background: BackgroundTasks, user: dict = Depends(security.active_user)):
    if not _DATE.match(body.birth_date):
        raise HTTPException(status_code=422, detail="Fecha inválida (usa AAAA-MM-DD).")
    rconn = read_conn()
    try:
        ok = db.verify_swimmer_birth(rconn, body.swimmer_id, body.birth_date)
        summary = db.swimmer_summary(rconn, body.swimmer_id) if ok else None
    finally:
        rconn.close()
    if not ok:  # mismo mensaje exista o no el nadador: no revela datos
        raise HTTPException(status_code=400, detail="No pudimos verificar al nadador con esa fecha.")
    conn = app_conn()
    try:
        db.set_user_swimmer(conn, _uid(user), body.swimmer_id)
    finally:
        conn.close()
    background.add_task(_enrich, body.swimmer_id)
    return {"swimmer": summary}


@router.delete("/swimmer", status_code=status.HTTP_204_NO_CONTENT)
def unlink_swimmer(user: dict = Depends(security.active_user)):
    conn = app_conn()
    try:
        db.set_user_swimmer(conn, _uid(user), None)
    finally:
        conn.close()


@router.put("/following/{swimmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def follow(swimmer_id: str, background: BackgroundTasks, user: dict = Depends(security.active_user)):
    summary = _summary(swimmer_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Nadador no encontrado.")
    conn = app_conn()
    try:
        db.follow_swimmer(conn, _uid(user), swimmer_id, summary["swimmer_name"])
    finally:
        conn.close()
    background.add_task(_enrich, swimmer_id)  # el torneo de sus marcas, sin hacer esperar al usuario


def _enrich(swimmer_id: str) -> None:
    """Historial completo del nadador, en segundo plano (abre y cierra su propia conexión)."""
    try:
        historial.enrich_swimmer(app_conn, swimmer_id)
    except Exception:
        pass


@router.delete("/following/{swimmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def unfollow(swimmer_id: str, user: dict = Depends(security.active_user)):
    conn = app_conn()
    try:
        db.unfollow_swimmer(conn, _uid(user), swimmer_id)
    finally:
        conn.close()


@router.post("/password")
@limiter.limit("5/minute")
def change_password(request: Request, body: PasswordBody, user: dict = Depends(security.active_user)):
    """Cambia la contraseña y cierra las demás sesiones; devuelve un token nuevo (como /auth/login)."""
    conn = app_conn()
    try:
        try:
            db.change_password(conn, _uid(user), body.current, body.new)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        row = db.get_user_by_id(conn, _uid(user))
    finally:
        conn.close()
    security.clear_role_cache(user["id"])
    return {"token": security.create_token(row), "email": row["email"], "role": row["role"],
            "permissions": user["permissions"]}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user: dict = Depends(security.active_user)):
    conn = app_conn()
    try:
        db.delete_user(conn, _uid(user))
    finally:
        conn.close()
