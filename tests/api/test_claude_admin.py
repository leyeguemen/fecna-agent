"""Tests de /ask con Claude (cliente simulado), guard SQL y endpoints /admin."""

from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from fecna_agent import claude_agent, db
from fecna_agent.sql_guard import check_select


def _row(**kw):
    base = dict(source="t", ranking_position=1, swimmer_id="1", swimmer_name="Ana Perez",
                first_name="Ana", last_name="Perez", gender="F", birth_date="2008-05-01",
                birth_year_month="2008-05", event_id="E1", event_name="100 libre",
                pool_type="LC", time_raw="01:00.00", time_ms=60000, points=500,
                result_date="2026-01-01", league="Valle", club="Club", fetched_at="2026-01-02")
    base.update(kw)
    return base


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.db")
    db.insert_results(c, [_row(), _row(swimmer_id="2", swimmer_name="Bea Gil", time_ms=59000,
                                       time_raw="00:59.00")])
    return c


@pytest.mark.parametrize("sql", [
    "SELECT * FROM ranking_public",
    "SELECT COUNT(*) FROM ranking_public WHERE club LIKE '%drop%'",
    "WITH t AS (SELECT * FROM ranking_public) SELECT * FROM t",
    "SELECT EXTRACT(YEAR FROM now()) FROM catalogs",
    # Consultas típicas del chat: agregados, ventanas, subconsultas, uniones entre tablas permitidas.
    "SELECT club, COUNT(DISTINCT swimmer_id) AS n FROM ranking_public GROUP BY club ORDER BY n DESC LIMIT 10",
    "SELECT swimmer_name, MIN(time_ms) FROM ranking_public WHERE event_name ILIKE '%libre%' AND pool_type = 'LC' GROUP BY swimmer_name",
    "SELECT * FROM (SELECT swimmer_name, time_ms, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY time_ms) AS pos FROM ranking_public) t WHERE pos <= 3",
    "SELECT e.swimmer_name, c.name FROM competition_entry e JOIN competition c ON c.id = e.competition_id",
    "SELECT code, label FROM catalogs WHERE kind = 'prueba' AND lower(label) LIKE '%100%'",
    "SELECT ROUND(AVG(points), 1), CAST(SUBSTR(result_date, 1, 4) AS INTEGER) AS y FROM ranking_public GROUP BY y",
    "SELECT CASE WHEN time_ms < 60000 THEN 'sub 1' ELSE 'más' END, COALESCE(club, '-') FROM ranking_public",
    "WITH a AS (SELECT * FROM ranking_public), b AS (SELECT * FROM a) SELECT COUNT(*) FROM b",
    "SELECT swimmer_name FROM ranking_public UNION SELECT swimmer_name FROM competition_entry",
])
def test_guard_permite(sql):
    assert check_select(sql)


@pytest.mark.parametrize("sql", [
    "DELETE FROM ranking_public",
    "SELECT * FROM app_user",
    "SELECT * FROM ranking_results",  # tabla base con fecha de nacimiento exacta
    "SELECT 1; DROP TABLE x",
    "SELECT * FROM pg_shadow",
    "SELECT * FROM information_schema.tables",
    # Ataques que pasaban el filtro de expresiones regulares (auditoría 2026-11-23).
    "SELECT email FROM ranking_public, app_user",
    "SELECT birth_date FROM catalogs , ranking_results LIMIT 1",
    "SELECT * FROM ranking_public r, (SELECT 1) x, app_user u",
    "SELECT query_to_xml('select email, password_hash from app_user', true, true, '')",
    "SELECT set_config('statement_timeout', '0', false)",
    "SELECT pg_sleep(30)",
    "SELECT dblink('host=x', 'select 1')",
    "SELECT * FROM generate_series(1, 100000000000)",
    "SELECT * FROM public.app_user",
    "SELECT * INTO copia FROM ranking_public",
    "SELECT * FROM ranking_public FOR UPDATE",
    "SELECT current_user",
    # Un CTE no puede «tapar» una tabla prohibida: dentro de su propio cuerpo se refiere a la real.
    "WITH app_user AS (SELECT * FROM app_user) SELECT * FROM app_user",
    "SELECT * FROM (WITH app_user AS (SELECT 1) SELECT * FROM app_user) x, app_user",
    "WITH RECURSIVE t(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM t) SELECT * FROM t",
    "SELECT * FROM ranking_public WHERE swimmer_id IN (SELECT CAST(id AS TEXT) FROM app_user)",
])
def test_guard_rechaza(sql):
    with pytest.raises(ValueError):
        check_select(sql)


def test_sql_libre_en_sqlite_corre_en_solo_lectura(conn):
    """Segunda capa: aunque algo se colara por la guarda, la conexión no deja escribir."""
    import sqlite3

    with pytest.raises(sqlite3.OperationalError):
        claude_agent._run_readonly(conn, "DELETE FROM ranking_results")
    assert conn.execute("SELECT COUNT(*) FROM ranking_results").fetchone()[0] == 2
    conn.execute("DELETE FROM sync_log")  # al terminar, la conexión vuelve a permitir escribir


def test_sql_libre_en_postgres_usa_transaccion_de_solo_lectura_con_tiempo_maximo():
    from fecna_agent.pg import PgConnection

    sent = []

    class FakeCursor:
        def execute(self, sql, params=None):
            sent.append(sql)

        def fetchmany(self, n):
            return []

    class FakeRaw:
        def cursor(self, row_factory=None):
            return FakeCursor()

        def commit(self):
            sent.append("COMMIT")

        def rollback(self):
            sent.append("ROLLBACK")

    claude_agent._run_readonly(PgConnection(FakeRaw()), "SELECT 1")
    assert sent[0] == "COMMIT" and sent[1] == "SET TRANSACTION READ ONLY"
    assert sent[2].startswith("SET LOCAL statement_timeout")
    assert sent[3] == "SELECT 1" and sent[-1] == "ROLLBACK"


def test_consultar_no_expone_birth_date(conn):
    out = claude_agent.run_tool(conn, "consultar", {"sql": "SELECT birth_date FROM ranking_public"})
    assert "Error" in out and "2008-05-01" not in out


def test_herramientas_ocultan_fecha_de_nacimiento(conn):
    out = claude_agent.run_tool(conn, "ranking", {"event_id": "E1", "pool_type": "LC"})
    assert "Bea Gil" in out and "2008" not in out


def test_answer_ejecuta_herramienta_y_responde(conn):
    calls = []

    class FakeMessages:
        def create(self, **kw):
            calls.append(kw)
            if len(calls) == 1:
                block = NS(type="tool_use", id="t1", name="mejor_marca",
                           input={"swimmer_id": "2"})
                return NS(stop_reason="tool_use", content=[block])
            result = kw["messages"][-1]["content"][0]["content"]
            return NS(stop_reason="end_turn", content=[NS(type="text", text=f"OK {result}")])

    reply = claude_agent.answer(conn, "mejor marca de Bea", client=NS(messages=FakeMessages()))
    assert "00:59.00" in reply and len(calls) == 2


@pytest.fixture
def api(tmp_path, monkeypatch):
    path = tmp_path / "r.db"
    db.connect(path).close()
    monkeypatch.setenv("FECNA_DB", str(path))
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app.db"))
    from api import main, security

    c = TestClient(main.app)

    def as_role(role):
        # Las acciones de admin leen el rol vigente de la base: el usuario tiene que existir.
        conn = db.connect(tmp_path / "app.db")
        email = f"{role}@y.co"
        row = db.get_user_by_email(conn, email)
        if row is None:
            db.create_user(conn, email, "clave12345", role=role)
            row = db.get_user_by_email(conn, email)
        conn.close()
        c.headers["Authorization"] = "Bearer " + security.create_token(row)
        return c

    return as_role


def test_ask_usa_claude_con_limite_diario(api, monkeypatch):
    from api.routers import ask as ask_mod

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("FECNA_ASK_DAILY_LIMIT", "1")
    ask_mod._usage.clear()
    monkeypatch.setattr(claude_agent, "answer", lambda conn, q, h=None, client=None: "hola!")
    c = api("user")
    assert c.post("/ask", json={"question": "x"}).json()["reply"] == "hola!"
    assert c.post("/ask", json={"question": "x"}).status_code == 429


def test_admin_requiere_rol_admin(api):
    c = api("user")
    assert c.post("/admin/sync", json={}).status_code == 403
    assert c.get("/admin/sync/status").status_code == 403


def test_admin_sync_despacha_workflow(api, monkeypatch):
    sent = {}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, json=json)
        return NS(status_code=204)

    from api.routers import admin

    monkeypatch.setattr(admin.requests, "post", fake_post)
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPO", "o/r")
    c = api("admin")
    assert c.post("/admin/sync", json={}).status_code == 202  # sin fecha: incremental
    assert sent["url"].endswith("/o/r/actions/workflows/sync.yml/dispatches")
    assert sent["json"]["inputs"] == {"modo": "incremental"}
    assert c.post("/admin/sync", json={"modo": "completa"}).status_code == 202
    assert sent["json"]["inputs"] == {"modo": "completa"}
    assert c.post("/admin/sync", json={"modo": "otro"}).status_code == 422
    # clientes antiguos que aún mandan una fecha: se ignora y queda incremental
    assert c.post("/admin/sync", json={"inicio": "2026-01-01"}).status_code == 202
    assert sent["json"]["inputs"] == {"modo": "incremental"}


def test_admin_sync_sin_configurar_503(api, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    c = api("admin")
    assert c.post("/admin/sync", json={}).status_code == 503
    st = c.get("/admin/sync/status")
    assert st.status_code == 200 and st.json()["run"] is None
