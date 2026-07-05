"""Doble conexión de base para la API: lectura pública y escritura de app.

- read_conn(): SQLite de solo lectura sobre la base pública anonimizada.
- app_conn(): Turso (prod, si hay credenciales) o SQLite local (dev/tests).

El env se resuelve en el momento de la llamada (no en el import) para que
los tests puedan usar monkeypatch.setenv sin recargar el módulo.
"""

import os
import sqlite3

from fecna_agent import db


def read_conn() -> sqlite3.Connection:
    """Conexión de solo lectura a la base pública (anonimizada)."""
    db_path = os.environ.get("FECNA_DB", "data/fecna_public.db")
    return db.connect(db_path)


def app_conn():
    """Conexión a la base de la app: Turso en prod, SQLite local en dev/tests."""
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    if turso_url:
        return _turso_conn(turso_url)
    return db.connect(os.environ.get("FECNA_APP_DB", "data/fecna_app.db"))


def _turso_conn(turso_url: str):
    try:
        import libsql
    except ImportError as exc:
        raise RuntimeError(
            "No se pudo importar 'libsql'. Instala la dependencia de producción "
            "(ver api/requirements.txt) para conectar a Turso."
        ) from exc

    auth_token = os.environ.get("TURSO_AUTH_TOKEN")
    try:
        conn = libsql.connect(turso_url, auth_token=auth_token)
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo conectar a Turso ({turso_url}). Revisa TURSO_DATABASE_URL "
            "y TURSO_AUTH_TOKEN."
        ) from exc

    # Asegura el esquema de forma idempotente (igual que fecna_agent.db.connect).
    for statement in db.SCHEMA.split(";"):
        statement = statement.strip()
        if statement:
            conn.execute(statement)
    conn.commit()
    return conn
