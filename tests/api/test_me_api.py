"""Tests de /me/* (vínculo de nadador, seguidos, contraseña, borrado) y /swimmers/compare."""

import pytest
from fastapi.testclient import TestClient

from fecna_agent import db


def _row(sid, name, ms, birth="2008-05-01"):
    return dict(source="t", ranking_position=1, swimmer_id=sid, swimmer_name=name,
                first_name=name, last_name="X", gender="F", birth_date=birth,
                birth_year_month=birth[:7], event_id="E1", event_name="100 libre",
                pool_type="LC", time_raw="01:00.00", time_ms=ms, points=1,
                result_date="2026-01-01", league="Valle", club="Club", fetched_at="2026-01-02")


@pytest.fixture
def client(tmp_path, monkeypatch):
    read = tmp_path / "read.db"
    c = db.connect(read)
    db.insert_results(c, [_row("1", "Ana Perez", 60000), _row("2", "Bea Gil", 59000, "2009-01-01")])
    c.close()
    monkeypatch.setenv("FECNA_DB", str(read))
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app.db"))
    from api import main

    cl = TestClient(main.app)
    r = cl.post("/auth/register", json={"email": "u@test.co", "password": "clave1234"})
    cl.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return cl


def test_vincular_nadador_verifica_fecha(client):
    bad = client.put("/me/swimmer", json={"swimmer_id": "1", "birth_date": "2000-01-01"})
    assert bad.status_code == 400
    ok = client.put("/me/swimmer", json={"swimmer_id": "1", "birth_date": "2008-05-01"})
    assert ok.status_code == 200 and ok.json()["swimmer"]["swimmer_name"] == "Ana Perez"
    assert client.get("/me").json()["swimmer"]["swimmer_id"] == "1"
    assert client.delete("/me/swimmer").status_code == 204
    assert client.get("/me").json()["swimmer"] is None


def test_seguir_y_dejar_de_seguir(client):
    assert client.put("/me/following/2").status_code == 204
    assert [f["swimmer_name"] for f in client.get("/me").json()["following"]] == ["Bea Gil"]
    assert client.put("/me/following/999").status_code == 404
    client.delete("/me/following/2")
    assert client.get("/me").json()["following"] == []


def test_cambiar_contrasena(client):
    assert client.post("/me/password", json={"current": "mala", "new": "nueva1234"}).status_code == 400
    assert client.post("/me/password", json={"current": "clave1234", "new": "corta"}).status_code == 400
    assert client.post("/me/password", json={"current": "clave1234", "new": "nueva1234"}).status_code == 204
    ok = client.post("/auth/login", json={"email": "u@test.co", "password": "nueva1234"})
    assert ok.status_code == 200


def test_eliminar_cuenta_borra_todo(client):
    client.put("/me/following/2")
    assert client.delete("/me").status_code == 204
    assert client.post("/auth/login", json={"email": "u@test.co", "password": "clave1234"}).status_code == 401


def test_comparar_nadadores(client):
    r = client.get("/swimmers/compare?a=1&b=2&event_id=E1&pool=LC").json()
    assert r["a"]["swimmer_name"] == "Ana Perez" and r["diff_ms"] == 1000
