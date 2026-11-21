"""Prueba de humo contra Postgres REAL (Supabase). Solo lectura.

Se omite si no hay DATABASE_URL (variable de entorno o .env). Verifica que las
consultas con funciones de ventana y la vista pública funcionan en Postgres.
"""

import os

import pytest

# El .env se lee SIN volcarlo al entorno: así el resto de la suite nunca toca la base real.
try:
    from dotenv import dotenv_values

    _env = dotenv_values()
except ImportError:
    _env = {}

URL = os.environ.get("FECNA_LIVE_DATABASE_URL") or _env.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="sin DATABASE_URL en .env (o FECNA_LIVE_DATABASE_URL)")

from fecna_agent import claude_agent, db  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    c = db.connect(URL)
    yield c
    c.close()


@pytest.fixture(scope="module")
def sample(conn):
    row = conn.execute(
        "SELECT swimmer_id, event_id, pool_type FROM ranking_results "
        "GROUP BY swimmer_id, event_id, pool_type ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    assert row, "la base está vacía: corre la migración"
    return row


def test_ranking_con_row_number(conn, sample):
    rows = db.ranking(conn, sample["event_id"], sample["pool_type"], None, 5)
    assert rows and rows[0]["time_ms"] <= rows[-1]["time_ms"]
    ids = [r["swimmer_id"] for r in rows]
    assert len(ids) == len(set(ids))  # un resultado por nadador


def test_swimmer_event_ranks(conn, sample):
    assert db.swimmer_event_ranks(conn, sample["swimmer_id"])


def test_best_time_e_historial(conn, sample):
    assert db.best_time(conn, sample["swimmer_id"], sample["event_id"], sample["pool_type"])
    assert db.history(conn, sample["swimmer_id"], sample["event_id"], sample["pool_type"])


def test_vista_publica_sin_fecha_exacta(conn):
    row = conn.execute("SELECT * FROM ranking_public LIMIT 1").fetchone()
    assert "birth_date" not in row.keys() and "birth_year" in row.keys()


def test_consultar_en_postgres_es_solo_lectura(conn):
    conn.execute("SET TRANSACTION READ ONLY")
    ok = claude_agent.run_tool(conn, "consultar",
                               {"sql": "SELECT COUNT(*) AS n FROM ranking_public"})
    assert "n" in ok
    bad = claude_agent.run_tool(conn, "consultar", {"sql": "DELETE FROM ranking_results"})
    assert "rechazada" in bad
    conn.rollback()


def test_fetchmany_en_cursor_postgres(conn):
    rows = conn.execute("SELECT swimmer_id FROM ranking_public").fetchmany(3)
    assert len(rows) == 3


def test_cuenta_y_alertas_en_postgres(conn, sample):
    # Migración aplicada y consultas nuevas válidas en Postgres (solo lectura).
    assert db.swimmer_summary(conn, sample["swimmer_id"])
    assert db.verify_swimmer_birth(conn, sample["swimmer_id"], "1900-01-01") is False
    comp = conn.execute("SELECT id FROM competition LIMIT 1").fetchone()
    assert isinstance(db.watched_schedule(conn, comp["id"], 0), list)
    assert db.list_following(conn, 0) == []
    cols = {r["column_name"] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'app_user'")}
    assert "swimmer_id" in cols


def test_esquema_no_se_reaplica_en_cada_conexion():
    """El DDL (bloqueos exclusivos) solo corre si falta algo, no en cada petición."""
    import time

    db._PG_SCHEMA_READY.clear()
    first = db.connect(URL); first.close()  # verifica con consultas de catálogo
    t = time.time()
    for _ in range(5):
        db.connect(URL).close()
    assert URL in db._PG_SCHEMA_READY
    assert time.time() - t < 20  # sin DDL por conexión (la mayor parte es la red)
