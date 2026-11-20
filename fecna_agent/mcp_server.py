"""Servidor MCP de solo lectura sobre la base FECNA.

Uso (stdio):  python -m fecna_agent.mcp_server
Base: variable FECNA_DB (por defecto data/fecna.db).

Seguridad: conexión SQLite en modo solo lectura + authorizer que solo permite
SELECT sobre ranking_results y catalogs (nunca app_user ni tablas de usuarios).
"""

import os
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import db as database

ALLOWED_TABLES = {"ranking_results", "catalogs", "sync_log", "competition", "competition_entry"}
MAX_ROWS = 200

mcp = FastMCP("fecna")


def _conn() -> sqlite3.Connection:
    path = Path(os.environ.get("FECNA_DB", database.DEFAULT_DB_PATH)).resolve()
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    def authorizer(action, arg1, arg2, dbname, source):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            return sqlite3.SQLITE_OK if arg1 in ALLOWED_TABLES else sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_PRAGMA and arg1 == "table_info":
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    conn.set_authorizer(authorizer)
    return conn


def _fmt(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return "(sin resultados)"
    cols = rows[0].keys()
    lines = [" | ".join(cols)]
    lines += [" | ".join("" if r[c] is None else str(r[c]) for c in cols) for r in rows]
    return "\n".join(lines)


@mcp.tool()
def esquema() -> str:
    """Tablas y columnas consultables. Úsala antes de escribir SQL."""
    conn = _conn()
    out = []
    for t in sorted(ALLOWED_TABLES):
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({t})")]
        if cols:
            out.append(f"{t}({', '.join(cols)})")
    out.append("Notas: time_ms = tiempo en milisegundos (menor es mejor); "
               "pool_type LC/SC; gender M/F.")
    return "\n".join(out)


@mcp.tool()
def consultar(sql: str) -> str:
    """Ejecuta UN SELECT de solo lectura (máx. 200 filas). Para estadísticas y agregados."""
    if ";" in sql.strip().rstrip(";"):
        return "Solo se permite una sentencia."
    try:
        rows = _conn().execute(sql.strip().rstrip(";")).fetchmany(MAX_ROWS)
    except sqlite3.Error as e:
        return f"Error SQL: {e}"
    return _fmt(rows)


@mcp.tool()
def buscar_nadador(nombre: str) -> str:
    """Busca nadadores por nombre (parcial). Devuelve swimmer_id, club y liga."""
    rows = _conn().execute(
        """SELECT DISTINCT swimmer_id, swimmer_name, gender, birth_date, club, league
           FROM ranking_results WHERE swimmer_name LIKE ? LIMIT 25""",
        (f"%{nombre}%",),
    ).fetchall()
    return _fmt(rows)


@mcp.tool()
def ranking(event_id: str, pool_type: str | None = None, gender: str | None = None,
            league: str | None = None, limit: int = 20,
            date_from: str | None = None, date_to: str | None = None) -> str:
    """Ranking por mejor marca en una prueba (event_id; ver tabla catalogs)."""
    return _fmt(database.ranking(_conn(), event_id, pool_type, gender,
                                 min(limit, MAX_ROWS), league,
                                 date_from=date_from, date_to=date_to))


@mcp.tool()
def mejor_marca(swimmer_id: str, event_id: str | None = None,
                pool_type: str | None = None) -> str:
    """Mejor marca de un nadador, opcionalmente por prueba y piscina."""
    row = database.best_time(_conn(), swimmer_id, event_id, pool_type)
    return _fmt([row] if row else [])


@mcp.tool()
def evolucion(swimmer_id: str, event_id: str | None = None,
              pool_type: str | None = None) -> str:
    """Historial cronológico de marcas de un nadador."""
    return _fmt(database.history(_conn(), swimmer_id, event_id, pool_type)[:MAX_ROWS])


if __name__ == "__main__":
    mcp.run()
