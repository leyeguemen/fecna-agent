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


def test_vincular_acepta_la_fecha_con_dia_y_mes_invertidos(client):
    """FECNA guarda a veces 5-dic como 12-may: la fecha real del padre debe poder verificar."""
    # El nadador «1» figura con 2008-05-01 (1 de mayo); la fecha real sería 2008-01-05 (5 de enero).
    assert client.put("/me/swimmer", json={"swimmer_id": "1", "birth_date": "2008-01-05"}).status_code == 200
    # Un día imposible de invertir (>12) o una fecha distinta siguen rechazándose.
    assert client.put("/me/swimmer", json={"swimmer_id": "1", "birth_date": "2008-06-01"}).status_code == 400
    assert client.put("/me/swimmer", json={"swimmer_id": "1", "birth_date": "2008-05-02"}).status_code == 400


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


def test_perfil_no_expone_fecha_de_nacimiento_exacta(client):
    """La fecha exacta es el secreto del vínculo de cuenta: el perfil solo da el año."""
    r = client.get("/swimmers/1").json()
    assert "birth_date" not in r and r["birth_year"] == "2008"
    assert "2008-05-01" not in client.get("/swimmers/1/ficha").text


def test_historial_incluye_puntos_y_ficha_descargable(client):
    h = client.get("/swimmers/1/history").json()["items"][0]
    assert h["points"] == 1
    f = client.get("/swimmers/1/ficha")
    assert f.status_code == 200 and "Ana Perez" in f.text
    assert client.get("/swimmers/999/ficha").status_code == 404


def test_registro_guarda_la_aceptacion_de_terminos(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app2.db"))
    monkeypatch.setenv("FECNA_DB", str(tmp_path / "read.db"))
    from api import main
    from fecna_agent import db as dbm

    cl = TestClient(main.app)
    assert cl.post("/auth/register", json={"email": "a@t.co", "password": "clave1234", "accept_terms": True}).status_code == 201
    assert cl.post("/auth/register", json={"email": "b@t.co", "password": "clave1234"}).status_code == 201  # cliente antiguo
    conn = dbm.connect(tmp_path / "app2.db")
    rows = {r["email"]: (r["terms_version"], r["terms_accepted_at"]) for r in conn.execute("SELECT email, terms_version, terms_accepted_at FROM app_user")}
    assert rows["a@t.co"][0] and rows["a@t.co"][1]
    assert rows["b@t.co"] == (None, None)


def test_historial_del_nadador_incluye_las_marcas_del_historial_completo(client, tmp_path):
    """/swimmers/{id}/history une el ranking con las marcas extra del Historial Deportivo."""
    import os

    conn = db.connect(os.environ["FECNA_DB"])
    conn.execute(
        "INSERT INTO swimmer_mark (swimmer_id, event_id, event_name, pool_type, time_ms, result_date, points, tournament) "
        "VALUES ('1','E1','100 libre','LC',65000,'2022-04-02',150,'TORNEO 2022')")
    conn.commit()
    conn.close()
    items = client.get("/swimmers/1/history").json()["items"]
    assert [i["date"] for i in items] == ["2022-04-02", "2026-01-01"]
    assert items[0]["tournament"] == "TORNEO 2022" and items[0]["points"] == 150
    assert len(client.get("/swimmers/1/history", params={"event_id": "E1", "pool": "LC"}).json()["items"]) == 2
