"""Torneo de cada marca: guardado por coincidencia exacta y tolerante a fallos de FECNA."""

from fecna_agent import db, historial


def _conn(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    conn.execute(
        "INSERT INTO ranking_results (source, swimmer_id, swimmer_name, event_id, event_name, pool_type, "
        "time_raw, time_ms, result_date) VALUES ('t','1','ANA','2','50m Libre','LC','00:00:30.97',30970,'2026-10-09')"
    )
    conn.execute("INSERT INTO swimmer_follow (user_id, swimmer_id, swimmer_name) VALUES (1,'1','ANA')")
    conn.commit()
    return conn


def test_enrich_guarda_torneo_de_marca_conocida(tmp_path, monkeypatch):
    conn = _conn(tmp_path)
    monkeypatch.setattr(historial, "fetch_tournaments", lambda sid, ev, delay=0, **k: [
        {"event_id": "2", "pool": "LC", "time_ms": 30970, "date": "2026-10-09", "tournament": "6A COPA ESTURIONES"},
        {"event_id": "2", "pool": "LC", "time_ms": 99999, "date": "2026-10-09", "tournament": "NO EXISTE EN LA BASE"},
    ])
    assert historial.enrich_tracked(conn, delay=0) == (1, 1)
    assert db.history(conn, "1")[0]["tournament"] == "6A COPA ESTURIONES"


def test_enrich_no_lanza_si_fecna_falla(tmp_path, monkeypatch):
    conn = _conn(tmp_path)
    def boom(*a, **k): raise RuntimeError("500")
    monkeypatch.setattr(historial, "fetch_tournaments", boom)
    assert historial.enrich_swimmer(conn, "1", delay=0) == 0
    assert db.history(conn, "1")[0]["tournament"] is None
