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
])
def test_guard_rechaza(sql):
    with pytest.raises(ValueError):
        check_select(sql)


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
