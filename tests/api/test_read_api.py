"""Tests de los endpoints de lectura: /catalogs, /rankings, /swimmers/*."""

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from fecna_agent import db

_HOY = dt.date.today().year


def _row(**over):
    base = {
        "source": "test",
        "ranking_position": None,
        "first_name": None,
        "last_name": None,
        "gender": "F",
        "birth_date": None,
        "birth_year_month": None,
        "event_id": "50L",
        "event_name": "50m Libre",
        "pool_type": "LC",
        "time_raw": "00:00:30.00",
        "time_ms": 30000,
        "points": None,
        "result_date": "2026-01-01",
        "league": None,
        "club": None,
        "fetched_at": None,
    }
    base.update(over)
    return base


def _rows():
    return [
        # 50L / LC / F: Maria (28500) < Ana (30000)
        _row(swimmer_id="1", swimmer_name="Ana Pérez", gender="F",
             birth_date=f"{_HOY - 16}-01-01", event_id="50L", pool_type="LC",
             time_raw="00:00:30.00", time_ms=30000, result_date="2026-01-10",
             league="Liga Andina", club="Club Delfines"),
        _row(swimmer_id="2", swimmer_name="Maria Lopez", gender="F",
             birth_date=f"{_HOY - 15}-01-01", event_id="50L", pool_type="LC",
             time_raw="00:00:28.50", time_ms=28500, result_date="2026-02-10",
             league="Liga Andina", club="Club Tiburones"),
        # 50L / LC / M: Juan (26000), más rápido que ambas F
        _row(swimmer_id="3", swimmer_name="Juan Garcia", gender="M",
             birth_date=f"{_HOY - 14}-01-01", event_id="50L", pool_type="LC",
             time_raw="00:00:26.00", time_ms=26000, result_date="2026-01-15",
             league="Liga Pacifico", club="Club Orcas"),
        # 50L / SC: Ana también nadó en piscina corta (para probar filtro pool)
        _row(swimmer_id="1", swimmer_name="Ana Pérez", gender="F",
             birth_date=f"{_HOY - 16}-01-01", event_id="50L", pool_type="SC",
             time_raw="00:00:29.00", time_ms=29000, result_date="2026-03-01",
             league="Liga Andina", club="Club Delfines"),
        # 100L / LC: Maria y Ana también nadaron esta prueba (para history/profile)
        _row(swimmer_id="2", swimmer_name="Maria Lopez", gender="F",
             birth_date=f"{_HOY - 15}-01-01", event_id="100L", event_name="100m Libre",
             pool_type="LC", time_raw="00:01:00.00", time_ms=60000,
             result_date="2026-01-20", league="Liga Andina", club="Club Tiburones"),
        _row(swimmer_id="1", swimmer_name="Ana Pérez", gender="F",
             birth_date=f"{_HOY - 16}-01-01", event_id="100L", event_name="100m Libre",
             pool_type="LC", time_raw="00:01:05.00", time_ms=65000,
             result_date="2026-04-01", league="Liga Andina", club="Club Delfines"),
    ]


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "read.db"
    conn = db.connect(db_path)
    db.insert_results(conn, _rows())
    db.save_catalogs(conn, {
        "prueba": [("50L", "50m Libre"), ("100L", "100m Libre")],
        "categoria_M": [("14 AÑOS", "14 AÑOS")],
        "categoria_F": [("15 AÑOS", "15 AÑOS"), ("16 AÑOS", "16 AÑOS")],
    })
    conn.close()

    monkeypatch.setenv("FECNA_DB", str(db_path))

    from api import main

    return TestClient(main.app)


def test_catalogs_ok(client):
    resp = client.get("/catalogs")
    assert resp.status_code == 200
    body = resp.json()
    assert {"id": "50L", "nombre": "50m Libre"} in body["pruebas"]
    assert {"id": "14 AÑOS", "nombre": "14 AÑOS"} in body["categorias"]
    assert body["piscinas"] == ["LC", "SC"]
    assert body["generos"] == ["M", "F"]


def test_catalogs_vacios_no_crashea(tmp_path, monkeypatch):
    db_path = tmp_path / "empty.db"
    db.connect(db_path).close()
    monkeypatch.setenv("FECNA_DB", str(db_path))
    from api import main
    resp = TestClient(main.app).get("/catalogs")
    assert resp.status_code == 200
    assert resp.json()["pruebas"] == []
    assert resp.json()["categorias"] == []


def test_rankings_orden_y_formato(client):
    resp = client.get("/rankings", params={"event_id": "50L", "pool": "LC"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["event_id"] == "50L"
    assert body["total"] == 3
    items = body["items"]
    assert [i["swimmer_id"] for i in items] == ["3", "2", "1"]
    assert [i["pos"] for i in items] == [1, 2, 3]
    assert items[0]["time_ms"] == 26000
    assert items[0]["time"] == "00:26.00"
    assert items[0]["club"] == "Club Orcas"
    assert items[0]["league"] == "Liga Pacifico"
    assert items[0]["date"] == "2026-01-15"


def test_rankings_filtro_genero(client):
    resp = client.get("/rankings", params={"event_id": "50L", "pool": "LC", "gender": "F"})
    body = resp.json()
    assert body["total"] == 2
    assert [i["swimmer_id"] for i in body["items"]] == ["2", "1"]


def test_rankings_filtro_pool(client):
    resp = client.get("/rankings", params={"event_id": "50L", "pool": "SC"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["swimmer_id"] == "1"
    assert body["items"][0]["time_ms"] == 29000


def test_rankings_filtro_categoria(client):
    resp = client.get(
        "/rankings",
        params={"event_id": "50L", "pool": "LC", "category": "14 AÑOS"},
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["swimmer_id"] == "3"


def test_rankings_limit(client):
    resp = client.get("/rankings", params={"event_id": "50L", "pool": "LC", "limit": 1})
    assert resp.json()["total"] == 1


def test_rankings_limit_excede_maximo(client):
    resp = client.get("/rankings", params={"event_id": "50L", "limit": 101})
    assert resp.status_code == 422


def test_swimmers_search_insensible_a_tildes(client):
    resp = client.get("/swimmers/search", params={"q": "perez"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["swimmer_id"] == "1"
    assert items[0]["swimmer_name"] == "Ana Pérez"
    assert items[0]["club"] == "Club Delfines"
    assert items[0]["league"] == "Liga Andina"


def test_swimmers_search_q_muy_corto(client):
    resp = client.get("/swimmers/search", params={"q": "an"})
    assert resp.status_code == 422


def test_swimmer_profile_ok(client):
    resp = client.get("/swimmers/1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["swimmer_id"] == "1"
    assert body["swimmer_name"] == "Ana Pérez"
    assert body["club"] == "Club Delfines"
    event_ids = {e["event_id"] for e in body["top_events"]}
    assert event_ids == {"50L", "100L"}
    for event in body["top_events"]:
        assert "best_time" in event
        assert "national_rank" in event


def test_swimmer_profile_404(client):
    resp = client.get("/swimmers/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Nadador no encontrado."


def test_swimmer_history_filtrado_por_prueba(client):
    resp = client.get("/swimmers/2/history", params={"event_id": "50L"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["event_id"] == "50L"
    assert items[0]["time_ms"] == 28500
    assert items[0]["time"] == "00:28.50"
    assert items[0]["date"] == "2026-02-10"


def test_swimmer_history_sin_filtro(client):
    resp = client.get("/swimmers/2/history")
    items = resp.json()["items"]
    assert len(items) == 2
    # Ordenado por fecha ascendente: 100L (2026-01-20) antes que 50L (2026-02-10).
    assert [i["event_id"] for i in items] == ["100L", "50L"]
