from fecna_agent import db


def _rows():
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
        "pool_type": "Larga",
        "time_raw": "00:30.00",
        "time_ms": 30000,
        "points": None,
        "result_date": "2026-01-01",
        "league": None,
        "club": None,
        "fetched_at": None,
    }
    return [
        {**base, "swimmer_id": "1", "swimmer_name": "Nadadora Uno"},
        {**base, "swimmer_id": "2", "swimmer_name": "Nadadora Dos", "time_ms": 31000,
         "time_raw": "00:31.00"},
    ]


def test_health_ok(tmp_path, monkeypatch):
    db_path = tmp_path / "read.db"
    conn = db.connect(db_path)
    db.insert_results(conn, _rows())
    conn.close()

    monkeypatch.setenv("FECNA_DB", str(db_path))

    from fastapi.testclient import TestClient

    from api import main

    client = TestClient(main.app)
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["resultados"] == 2
    assert body["nadadores"] == 2
