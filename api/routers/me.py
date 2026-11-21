"""Cuenta del usuario: nadador vinculado, nadadores seguidos, contraseña y borrado (/me/*)."""

import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from api import security
from api.deps import app_conn, read_conn
from api.routers.auth import limiter
from fecna_agent import db, historial

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


@router.get("")
def my_profile(user: dict = Depends(security.current_user)):
    conn = app_conn()
    try:
        swimmer_id = db.get_user_swimmer_id(conn, _uid(user))
        following = db.list_following(conn, _uid(user))
    finally:
        conn.close()
    return {"email": user["email"], "role": user["role"],
            "swimmer": _summary(swimmer_id), "following": following}


@router.put("/swimmer")
@limiter.limit("5/minute")  # frena la adivinanza de fechas de nacimiento
def link_swimmer(request: Request, body: LinkBody, background: BackgroundTasks, user: dict = Depends(security.current_user)):
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
def unlink_swimmer(user: dict = Depends(security.current_user)):
    conn = app_conn()
    try:
        db.set_user_swimmer(conn, _uid(user), None)
    finally:
        conn.close()


@router.put("/following/{swimmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def follow(swimmer_id: str, background: BackgroundTasks, user: dict = Depends(security.current_user)):
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
    conn = app_conn()
    try:
        historial.enrich_swimmer(conn, swimmer_id)
    except Exception:
        pass
    finally:
        conn.close()


@router.delete("/following/{swimmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def unfollow(swimmer_id: str, user: dict = Depends(security.current_user)):
    conn = app_conn()
    try:
        db.unfollow_swimmer(conn, _uid(user), swimmer_id)
    finally:
        conn.close()


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def change_password(request: Request, body: PasswordBody, user: dict = Depends(security.current_user)):
    conn = app_conn()
    try:
        try:
            db.change_password(conn, _uid(user), body.current, body.new)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        conn.close()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user: dict = Depends(security.current_user)):
    conn = app_conn()
    try:
        db.delete_user(conn, _uid(user))
    finally:
        conn.close()
