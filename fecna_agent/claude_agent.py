"""Agente conversacional con Claude (tool use) sobre la base FECNA.

Regla del proyecto: SQL/Python calcula, el modelo solo explica. Las
herramientas son de solo lectura; el SQL libre pasa por `sql_guard` y solo ve
la vista `ranking_public` (sin fecha de nacimiento exacta).
"""

import json
import os

from . import db as database
from .pg import PgConnection
from .sql_guard import MAX_ROWS, check_select

DEFAULT_MODEL = "claude-haiku-5-5"
MAX_TURNS = 6
SQL_TIMEOUT_MS = 5000  # tiempo máximo de una consulta libre del chat en Postgres


def _run_readonly(conn, sql: str):
    """Ejecuta el SQL libre del chat sin poder escribir (segunda capa tras sql_guard).

    Postgres: transacción READ ONLY con statement_timeout; al terminar se descarta (rollback).
    SQLite: PRAGMA query_only mientras dura la consulta.
    """
    if isinstance(conn, PgConnection):
        conn.commit()  # SET TRANSACTION debe ser lo primero de una transacción nueva
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute(f"SET LOCAL statement_timeout = {int(SQL_TIMEOUT_MS)}")
        try:
            return conn.execute(sql).fetchmany(MAX_ROWS)
        finally:
            conn.rollback()
    conn.execute("PRAGMA query_only = ON")
    try:
        return conn.execute(sql).fetchmany(MAX_ROWS)
    finally:
        conn.execute("PRAGMA query_only = OFF")

SYSTEM = (
    "Eres NATIA, el asistente de natación. Tus datos vienen del ranking de FECNA (Colombia). Responde en español, "
    "breve y con datos exactos: SIEMPRE obtén los números con las herramientas, nunca los "
    "inventes. Tiempos: muéstralos como mm:ss.cc usando time_raw. No muestres swimmer_id. "
    "Formato: texto plano, SIN markdown (nada de **, #, ni tablas); para listas usa líneas con guion. "
    "Si no encuentras datos, dilo. Si el nombre es ambiguo, pide aclarar. "
    "Usa `esquema` antes de escribir SQL con `consultar`. Para ranking necesitas el event_id "
    "real: búscalo con `consultar` en ranking_public (event_name) o en catalogs (kind='prueba'); "
    "nunca adivines ids."
)

TOOLS = [
    {"name": "esquema", "description": "Tablas y columnas consultables.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "consultar",
     "description": f"Un SELECT de solo lectura (máx. {MAX_ROWS} filas) para estadísticas y agregados.",
     "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}},
                      "required": ["sql"]}},
    {"name": "buscar_nadador", "description": "Busca nadadores por nombre parcial.",
     "input_schema": {"type": "object", "properties": {"nombre": {"type": "string"}},
                      "required": ["nombre"]}},
    {"name": "ranking",
     "description": "Ranking por mejor marca en una prueba (event_id del catálogo).",
     "input_schema": {"type": "object", "properties": {
         "event_id": {"type": "string"}, "pool_type": {"type": "string", "enum": ["LC", "SC"]},
         "gender": {"type": "string", "enum": ["M", "F"]}, "league": {"type": "string"},
         "limit": {"type": "integer"}}, "required": ["event_id"]}},
    {"name": "mejor_marca", "description": "Mejor marca de un nadador.",
     "input_schema": {"type": "object", "properties": {
         "swimmer_id": {"type": "string"}, "event_id": {"type": "string"},
         "pool_type": {"type": "string"}}, "required": ["swimmer_id"]}},
    {"name": "evolucion", "description": "Historial cronológico de marcas de un nadador.",
     "input_schema": {"type": "object", "properties": {
         "swimmer_id": {"type": "string"}, "event_id": {"type": "string"},
         "pool_type": {"type": "string"}}, "required": ["swimmer_id"]}},
]

_SAFE_COLS = ("swimmer_id", "swimmer_name", "gender", "event_id", "event_name", "pool_type",
              "time_raw", "time_ms", "result_date", "league", "club", "points")


def _fmt(rows) -> str:
    rows = list(rows)
    if not rows:
        return "(sin resultados)"
    cols = list(rows[0].keys())
    lines = [" | ".join(cols)]
    lines += [" | ".join("" if r[c] is None else str(r[c]) for c in cols) for r in rows]
    return "\n".join(lines)


def _safe(rows) -> list[dict]:
    """Quita columnas sensibles (fecha de nacimiento) de filas de db.*."""
    return [{c: r[c] for c in _SAFE_COLS if c in r.keys()} for r in rows]


def run_tool(conn, name: str, args: dict) -> str:
    """Ejecuta una herramienta; devuelve texto (los errores también, para que el modelo se corrija)."""
    try:
        if name == "esquema":
            return ("ranking_public(swimmer_id, swimmer_name, gender, birth_year, event_id, "
                    "event_name, pool_type, time_raw, time_ms, points, result_date, league, club, tournament; tournament solo está lleno para nadadores seguidos)\n"
                    "catalogs(kind, code, label)\n"
                    "competition(id, name, pool_type, loaded_at)\n"
                    "competition_entry(competition_id, event_label, session_date, heat, lane, "
                    "swimmer_name, club_code, age, seed_raw)\n"
                    "Notas: time_ms en milisegundos (menor es mejor); pool_type LC/SC; gender M/F.")
        if name == "consultar":
            sql = check_select(args["sql"], "postgres" if isinstance(conn, PgConnection) else "sqlite")
            return _fmt(_run_readonly(conn, sql))
        if name == "buscar_nadador":
            rows = conn.execute(
                """SELECT DISTINCT swimmer_id, swimmer_name, gender, club, league
                   FROM ranking_public WHERE swimmer_name LIKE ? LIMIT 25""",
                (f"%{args['nombre']}%",)).fetchall()
            return _fmt(rows)
        if name == "ranking":
            rows = database.ranking(
                conn, args["event_id"], args.get("pool_type"), args.get("gender"),
                min(int(args.get("limit", 20)), MAX_ROWS), args.get("league"))
            return _fmt(_safe(rows))
        if name == "mejor_marca":
            row = database.best_time(conn, args["swimmer_id"], args.get("event_id"),
                                     args.get("pool_type"))
            return _fmt(_safe([row]) if row else [])
        if name == "evolucion":
            rows = database.history(conn, args["swimmer_id"], args.get("event_id"),
                                    args.get("pool_type"))[:MAX_ROWS]
            return _fmt(_safe(rows))
        return f"Herramienta desconocida: {name}"
    except ValueError as exc:
        return f"Consulta rechazada: {exc}"
    except Exception as exc:  # error SQL u otro: el modelo puede reintentar
        return f"Error: {exc}"


def answer(conn, question: str, history: list[dict] | None = None, client=None) -> str:
    """Bucle de tool use. `history` = turnos previos [{role, content}] (solo texto)."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY
    model = os.environ.get("FECNA_CLAUDE_MODEL", DEFAULT_MODEL)
    if type(conn).__name__ == "PgConnection":  # defensa en profundidad además del guard
        conn.execute("SET TRANSACTION READ ONLY")
    messages = [m for m in (history or [])[-10:] if m.get("role") in ("user", "assistant")]
    messages.append({"role": "user", "content": question})

    for _ in range(MAX_TURNS):
        resp = client.messages.create(model=model, max_tokens=1024, system=SYSTEM,
                                      tools=TOOLS, messages=messages)
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text").strip()
        messages.append({"role": "assistant", "content": resp.content})
        results = [
            {"type": "tool_result", "tool_use_id": b.id,
             "content": run_tool(conn, b.name, b.input)}
            for b in resp.content if b.type == "tool_use"
        ]
        messages.append({"role": "user", "content": results})
    return "No pude completar la consulta; intenta reformular la pregunta."
