"""Marcas mínimas de los campeonatos nacionales: tabla por categoría y comparación con un nadador."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api import security
from api.deps import app_conn, read_conn
from fecna_agent import db, minimas

router = APIRouter(prefix="/minimas", tags=["minimas"])


def _check(tournament: str, category: str | None = None, gender: str | None = None) -> None:
    if tournament not in minimas.TOURNAMENTS:
        raise HTTPException(status_code=422, detail="Campeonato no válido.")
    if category is not None and category not in minimas.CATEGORIES[tournament]:
        raise HTTPException(status_code=422, detail="Categoría no válida para ese campeonato.")
    if gender is not None and gender not in minimas.GENDERS:
        raise HTTPException(status_code=422, detail="Género no válido (M o F).")


@router.get("/torneos")
def tournaments():
    conn = app_conn()  # las marcas mínimas viven con los datos de la app (donde las corrige el admin)
    try:
        years = db.minimum_years(conn)
    finally:
        conn.close()
    return {"items": [
        {"id": t, "label": label, "year": years.get(t),
         "categories": [{"id": c, "label": minimas.category_label(c)} for c in minimas.CATEGORIES[t]]}
        for t, label in minimas.TOURNAMENTS.items() if t in years]}


def _table(tournament: str, category: str, gender: str) -> dict[str, int]:
    conn = app_conn()
    try:
        return db.minimum_marks(conn, tournament, category, gender)
    finally:
        conn.close()


@router.get("/tabla")
def table(tournament: str, category: str, gender: str):
    _check(tournament, category, gender)
    marks = _table(tournament, category, gender)
    return {"tournament": tournament, "category": category, "category_label": minimas.category_label(category),
            "gender": gender,
            "rows": [{"event_id": e, "event": label, "minima_ms": marks[e], "minima": minimas.format_time(marks[e])}
                     for e, label in minimas.EVENTS if e in marks]}


@router.get("/nadador/{swimmer_id}")
def swimmer(swimmer_id: str, tournament: str = Query("interligas")):
    """Qué marcas mínimas cumple el nadador y cuánto le falta en las demás (piscina larga)."""
    _check(tournament)
    out = evaluate_swimmer(swimmer_id, tournament)
    if out is None:
        raise HTTPException(status_code=404, detail="Nadador no encontrado.")
    return out


def evaluate_swimmer(swimmer_id: str, tournament: str) -> dict | None:
    """Mínimas del nadador en ese campeonato (también la usa el Inicio). None si el nadador no existe."""
    mconn = app_conn()
    try:
        year = db.minimum_years(mconn).get(tournament)
    finally:
        mconn.close()
    conn = read_conn()
    try:
        ident = db.swimmer_identity(conn, swimmer_id)
        if ident is None:
            return None
        best = db.swimmer_bests(conn, swimmer_id, minimas.POOL)
        gender = (ident["gender"] or "").upper() or None
        birth_year = int(ident["birth_date"][:4]) if ident.get("birth_date") else None
        age = (year or date.today().year) - birth_year if birth_year else None
        category = minimas.category_for(tournament, age) if gender in minimas.GENDERS else None
    finally:
        conn.close()
    conn = app_conn()
    try:
        marks = db.minimum_marks(conn, tournament, category, gender, year) if category else {}
    finally:
        conn.close()
    out = {"swimmer_id": swimmer_id, "swimmer_name": ident["swimmer_name"], "club": ident["club"],
           "league": ident["league"], "gender": gender, "age": age, "tournament": tournament, "year": year,
           "category": category, "category_label": minimas.category_label(category) if category else None,
           "applicable": bool(category and marks), "rows": [], "met": 0, "total": 0}
    if out["applicable"]:
        out.update(minimas.evaluate(marks, best))
    return out


class MarksBody(BaseModel):
    marks: dict[str, str]  # event_id → "mm:ss,cc"; vacío = sin marca para esa prueba


@router.put("/{tournament}/{category}/{gender}")
def save(tournament: str, category: str, gender: str, body: MarksBody,
         admin: dict = Depends(security.require_permission("cargar_minimas"))):
    _check(tournament, category, gender)
    parsed: dict[str, int] = {}
    for event_id, text in body.marks.items():
        if event_id not in minimas.EVENT_LABEL:
            raise HTTPException(status_code=422, detail=f"Prueba desconocida: {event_id}")
        if not text.strip():
            continue
        try:
            parsed[event_id] = minimas.parse_time(text)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{minimas.EVENT_LABEL[event_id]}: {exc}")
    conn = app_conn()
    try:
        year = db.minimum_years(conn).get(tournament) or minimas.YEAR
        n = db.save_minimum_marks(conn, tournament, year, category, gender, parsed)
    finally:
        conn.close()
    return {"saved": n}
