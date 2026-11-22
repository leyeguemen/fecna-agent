"""Historial completo de FECNA: torneo de las marcas del ranking, marcas extra aparte y tolerancia a fallos."""

from fecna_agent import db, historial


def _conn(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    conn.execute(
        "INSERT INTO ranking_results (source, swimmer_id, swimmer_name, event_id, event_name, pool_type, "
        "time_raw, time_ms, result_date) VALUES ('t','1','ANA','2','50m Libre/50m Free','LC','00:00:30.97',30970,'2026-10-09')"
    )
    conn.execute("INSERT INTO swimmer_follow (user_id, swimmer_id, swimmer_name) VALUES (1,'1','ANA')")
    conn.commit()
    return conn


def _fake(monkeypatch, marks):
    monkeypatch.setattr(historial, "fetch_tournaments", lambda sid, ev, delay=0, **k: marks)


MARKS = [
    {"event_id": "2", "pool": "LC", "time_ms": 30970, "date": "2026-10-09", "tournament": "6A COPA ESTURIONES", "points": 308},
    {"event_id": "2", "pool": "LC", "time_ms": 33100, "date": "2023-05-20", "tournament": "TORNEO VIEJO", "points": 210},
    {"event_id": "2", "pool": "SC", "time_ms": 32000, "date": "2024-03-01", "tournament": "CHEQUEO", "points": None},
    {"event_id": "99", "pool": "LC", "time_ms": 1, "date": "2024-01-01", "tournament": "X", "points": 1},  # prueba desconocida
]


def test_el_historial_pone_torneo_a_la_marca_del_ranking_y_guarda_las_demas_aparte(tmp_path, monkeypatch):
    conn = _conn(tmp_path)
    _fake(monkeypatch, MARKS)
    assert historial.enrich_tracked(conn, delay=0) == (1, 3)  # 3 nuevas en swimmer_mark (la 99 se ignora)
    ranking = db.history(conn, "1")
    assert len(ranking) == 1 and ranking[0]["tournament"] == "6A COPA ESTURIONES"  # el ranking no se toca
    full = db.full_history(conn, "1")
    assert [(m["result_date"], m["time_ms"]) for m in full] == [("2023-05-20", 33100), ("2024-03-01", 32000), ("2026-10-09", 30970)]
    assert full[0]["tournament"] == "TORNEO VIEJO" and full[0]["points"] == 210 and full[0]["event_name"] == "50m Libre/50m Free"
    # La marca que está en el ranking no se duplica aunque también venga en el historial.
    assert sum(1 for m in full if m["time_ms"] == 30970) == 1


def test_repetir_la_actualizacion_no_duplica(tmp_path, monkeypatch):
    conn = _conn(tmp_path)
    _fake(monkeypatch, MARKS)
    historial.enrich_tracked(conn, delay=0)
    assert historial.enrich_tracked(conn, delay=0) == (1, 0)
    assert len(db.full_history(conn, "1")) == 3


def test_full_history_filtra_por_prueba_y_piscina(tmp_path, monkeypatch):
    conn = _conn(tmp_path)
    _fake(monkeypatch, MARKS)
    historial.enrich_tracked(conn, delay=0)
    assert [m["time_ms"] for m in db.full_history(conn, "1", event_id="2", pool_type="LC")] == [33100, 30970]
    assert [m["time_ms"] for m in db.full_history(conn, "1", pool_type="SC")] == [32000]
    assert db.full_history(conn, "otro") == []


def test_enrich_no_lanza_si_fecna_falla(tmp_path, monkeypatch):
    conn = _conn(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("500")

    monkeypatch.setattr(historial, "fetch_tournaments", boom)
    assert historial.enrich_swimmer(conn, "1", delay=0) == 0
    assert db.history(conn, "1")[0]["tournament"] is None
