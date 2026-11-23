"""/minimas: tabla por categoría, comparación con un nadador y corrección por el admin."""

import pytest
from fastapi.testclient import TestClient

from fecna_agent import db


def _row(sid, ms, event="2", gender="F", birth="2008-05-01", pool="LC"):
    return dict(source="t", ranking_position=1, swimmer_id=sid, swimmer_name="Ana Perez",
                first_name="Ana", last_name="Perez", gender=gender, birth_date=birth, birth_year_month=birth[:7],
                event_id=event, event_name="50m Libre", pool_type=pool, time_raw="x", time_ms=ms, points=1,
                result_date="2026-01-01", league="Valle", club="Club", fetched_at="2026-01-02")


@pytest.fixture
def env(tmp_path, monkeypatch):
    read = tmp_path / "read.db"
    c = db.connect(read)
    # Nacida en 2008 → 18 años en 2026 → Junior. Mínima interligas 50 L Junior F = 29,17.
    db.insert_results(c, [_row("1", 29000), _row("1", 28500, pool="SC"), _row("2", 30500, birth="2016-01-01")])
    c.close()
    monkeypatch.setenv("FECNA_DB", str(read))
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("FECNA_ADMIN_EMAIL", "boss@x.co")
    from api import main

    client = TestClient(main.app)

    def auth(email):
        r = client.post("/auth/register", json={"email": email, "password": "Secreta123"})
        return {"Authorization": f"Bearer {r.json()['token']}"}

    return client, auth


def test_tabla_y_torneos(env):
    client, auth = env
    h = auth("ana@x.co")
    items = client.get("/minimas/torneos", headers=h).json()["items"]
    assert {t["id"] for t in items} == {"infantiles", "interligas", "interclubes"}
    rows = client.get("/minimas/tabla", params={"tournament": "interligas", "category": "juvb", "gender": "M"}, headers=h).json()["rows"]
    assert len(rows) == 17 and rows[0] == {"event_id": "2", "event": "50 L", "minima_ms": 25550, "minima": "00:25,55"}
    assert client.get("/minimas/tabla", params={"tournament": "x", "category": "juvb", "gender": "M"}, headers=h).status_code == 422
    assert client.get("/minimas/tabla", params={"tournament": "infantiles", "category": "juvb", "gender": "M"}, headers=h).status_code == 422


def test_nadador_cumple_y_solo_cuenta_piscina_larga(env):
    client, auth = env
    r = client.get("/minimas/nadador/1", headers=auth("ana@x.co")).json()
    assert r["category"] == "junior" and r["age"] == 18 and r["applicable"]
    first = r["rows"][0]
    assert first["event"] == "50 L" and first["status"] == "cumple" and first["best_ms"] == 29000  # la de piscina corta no cuenta
    assert first["diff"] == "0,17 s" and r["met"] == 1


def test_nadador_sin_categoria_o_inexistente(env):
    client, auth = env
    h = auth("ana@x.co")
    little = client.get("/minimas/nadador/2", headers=h).json()
    assert little["applicable"] is False and little["category"] is None and little["rows"] == []
    assert client.get("/minimas/nadador/zzz", headers=h).status_code == 404


def test_solo_el_admin_corrige_marcas(env):
    client, auth = env
    user, admin = auth("ana@x.co"), auth("boss@x.co")
    url = "/minimas/interligas/junior/F"
    assert client.put(url, json={"marks": {"2": "00:29,00"}}, headers=user).status_code == 403
    assert client.put(url, json={"marks": {"2": "mal"}}, headers=admin).status_code == 422
    assert client.put(url, json={"marks": {"2": "00:29,00"}}, headers=admin).json() == {"saved": 1}
    r = client.get("/minimas/nadador/1", headers=user).json()
    assert r["total"] == 1 and r["rows"][0]["status"] == "cumple" and r["rows"][0]["minima"] == "00:29,00"
