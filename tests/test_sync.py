import pytest

from fecna_agent import db as database
from fecna_agent import sync

EVENTS = [("2", "50m Libre/50m Free"), ("6", "800m Libre/800m Free")]


def fake_fetch(inicio, fin, genero, categoria, prueba, piscina, session):
    """Un resultado distinto por combinación; determinístico para re-sync."""
    return [{
        "tiempo": "00:00:28.84",
        "identificacion": f"{prueba}{piscina}{genero}",
        "prueba_id": prueba,
        "piscina": piscina,
        "prueba": dict(EVENTS)[prueba],
        "nombre": "NADADOR", "apellido": genero, "nada": f"NADADOR {genero}",
        "genero": genero, "fecha_nac": "2014-08-03", "edad": "2014-08",
        "contador": 1, "puntos": 100, "fecha_tor": "2026-06-01",
        "nombre_liga": "LIGA", "nombre_club": "CLUB",
    }]


@pytest.fixture
def conn(monkeypatch):
    monkeypatch.setattr(sync.extractor, "fetch_ranking", fake_fetch)
    conn = database.connect(":memory:")
    database.save_catalogs(conn, {
        "prueba": EVENTS,
        "categoria_M": [("12 AÑOS", "12 AÑOS"), ("13 AÑOS", "13 AÑOS")],
        "categoria_F": [("12 AÑOS", "12 AÑOS"), ("13 AÑOS", "13 AÑOS")],
    })
    yield conn
    conn.close()


def test_sync_recorre_todas_las_combinaciones(conn):
    calls = []
    stats = sync.sync_all(
        conn, delay=0, progress=lambda done, total, d: calls.append((done, total)),
    )
    assert stats["combos"] == 8  # 2 pruebas × 2 piscinas × 2 géneros
    assert stats["inserted"] == 8
    assert stats["errors"] == 0
    assert calls[-1] == (8, 8)


def test_resync_es_idempotente_y_queda_en_bitacora(conn):
    sync.sync_all(conn, delay=0)
    stats = sync.sync_all(conn, delay=0)
    assert stats["inserted"] == 0  # nada nuevo: ya estaba al día

    last = database.last_sync(conn)
    assert last["inserted"] == 0
    assert last["combos"] == 8
    # La corrida sin novedades no tiene resultados asociados
    assert database.results_from_run(conn, stats["run_at"]) == []


def test_novedades_de_una_corrida(conn):
    stats = sync.sync_all(conn, delay=0)
    nuevos = database.results_from_run(conn, stats["run_at"])
    assert len(nuevos) == 8
    resumen = database.summarize_run(conn, stats["run_at"])
    assert sum(r["nuevos"] for r in resumen) == 8


def test_sync_envia_todas_las_categorias_del_genero(conn, monkeypatch):
    seen = []

    def spy(inicio, fin, genero, categoria, prueba, piscina, session):
        seen.append((genero, categoria))
        return []

    monkeypatch.setattr(sync.extractor, "fetch_ranking", spy)
    sync.sync_all(conn, delay=0)
    assert all(cats == ["12 AÑOS", "13 AÑOS"] for _, cats in seen)


def test_sync_sin_catalogo_de_categorias_falla_claro(conn):
    conn.execute("DELETE FROM catalogs WHERE kind LIKE 'categoria%'")
    with pytest.raises(RuntimeError, match="categorías"):
        sync.sync_all(conn, delay=0)


def test_errores_aislados_no_detienen_la_corrida(conn, monkeypatch):
    def flaky(inicio, fin, genero, categoria, prueba, piscina, session):
        if prueba == "2" and piscina == "SC":
            raise RuntimeError("timeout")
        return fake_fetch(inicio, fin, genero, categoria, prueba, piscina, session)

    monkeypatch.setattr(sync.extractor, "fetch_ranking", flaky)
    stats = sync.sync_all(conn, delay=0)
    assert stats["errors"] == 2   # 2 SC de la prueba 2: bajo el umbral del cortacircuito
    assert stats["inserted"] == 6
    assert not stats["aborted"]


def test_bloqueo_del_sitio_aborta_de_inmediato(conn, monkeypatch):
    calls = []

    def blocked(inicio, fin, genero, categoria, prueba, piscina, session):
        calls.append(prueba)
        raise sync.extractor.SiteBlockedError("verificación anti-bot")

    monkeypatch.setattr(sync.extractor, "fetch_ranking", blocked)
    stats = sync.sync_all(conn, delay=0)
    assert len(calls) == 1  # no insiste contra un sitio que está bloqueando
    assert "anti-bot" in stats["aborted"]


def test_errores_consecutivos_activan_el_cortacircuito(conn, monkeypatch):
    calls = []

    def always_fails(inicio, fin, genero, categoria, prueba, piscina, session):
        calls.append(prueba)
        raise RuntimeError("500 Server Error")

    monkeypatch.setattr(sync.extractor, "fetch_ranking", always_fails)
    stats = sync.sync_all(conn, delay=0)
    assert len(calls) == sync.MAX_CONSECUTIVE_ERRORS
    assert "errores consecutivos" in stats["aborted"]


def test_incremental_start_usa_ultima_marca_menos_margen(tmp_path):
    from datetime import date

    from fecna_agent import db, sync

    conn = db.connect(tmp_path / "t.db")
    assert sync.incremental_start(conn) == sync.BASE_START  # base vacía → desde el inicio
    row = dict(source="t", ranking_position=1, swimmer_id="1", swimmer_name="A B",
               first_name="A", last_name="B", gender="M", birth_date="2008-01-01",
               birth_year_month="2008-01", event_id="E", event_name="50 libre", pool_type="LC",
               time_raw="00:30.00", time_ms=30000, points=1, result_date="2026-11-10",
               league="L", club="C", fetched_at="2026-11-11")
    db.insert_results(conn, [row])
    assert sync.incremental_start(conn, 30, today=date(2026, 11, 20)) == "2026-10-11"
    assert sync.incremental_start(conn, 0, today=date(2026, 11, 5)) == "2026-11-05"  # nunca futuro
    assert sync.incremental_start(conn, 9999, today=date(2026, 11, 20)) == sync.BASE_START


def test_sync_divide_el_rango_si_el_sitio_responde_con_error(tmp_path, monkeypatch):
    """Un 500 por pedir demasiado de una vez no debe dejar la prueba sin datos."""
    from fecna_agent import db, extractor, normalizer, sync

    calls = []

    def fake_fetch(inicio, fin, session=None, **kw):
        from datetime import date

        calls.append((inicio, fin))
        if (date.fromisoformat(fin) - date.fromisoformat(inicio)).days > 100:
            import requests

            resp = requests.Response()
            resp.status_code = 500
            raise requests.HTTPError("500 Server Error", response=resp)
        return [{"rango": f"{inicio}..{fin}"}]

    monkeypatch.setattr(extractor, "build_session", lambda: None)
    monkeypatch.setattr(extractor, "fetch_ranking", fake_fetch)
    monkeypatch.setattr(normalizer, "normalize_rows", lambda raw, fetched_at=None: raw)
    monkeypatch.setattr(db, "insert_results", lambda conn, rows: len(rows))
    conn = db.connect(tmp_path / "t.db")

    stats = sync.sync_all(conn, inicio="2024-01-01", fin="2024-12-31", events=[("E", "Evento")],
                          pools=("LC",), genders=("F",), categoria="X", delay=0)

    assert stats["errors"] == 0 and stats["received"] >= 2  # se juntaron varios tramos
    assert calls[0] == ("2024-01-01", "2024-12-31")  # primero intenta todo el rango
    assert all(a <= b for a, b in calls)


def test_sync_no_divide_si_no_es_error_de_tamano(conn, monkeypatch):
    """Una caída de red no se multiplica en tramos: la corrida se corta como siempre."""
    calls = []

    def down(inicio, fin, genero, categoria, prueba, piscina, session):
        calls.append(1)
        raise ConnectionError("sin red")

    monkeypatch.setattr(sync.extractor, "fetch_ranking", down)
    sync.sync_all(conn, delay=0)
    assert len(calls) == sync.MAX_CONSECUTIVE_ERRORS


def test_sync_aisla_un_dia_danado_y_recupera_el_resto(tmp_path, monkeypatch):
    """FECNA rompe en un día concreto: se omite ese día y no se pierde el resto del rango."""
    from datetime import date, timedelta

    import requests

    from fecna_agent import db, extractor, normalizer, sync

    bad = date(2024, 6, 6)
    got = []

    def fake_fetch(inicio, fin, session=None, **kw):
        a, b = date.fromisoformat(inicio), date.fromisoformat(fin)
        if a <= bad <= b:
            resp = requests.Response()
            resp.status_code = 500
            raise requests.HTTPError("500 Server Error", response=resp)
        days = [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]
        got.extend(days)
        return days

    monkeypatch.setattr(extractor, "build_session", lambda: None)
    monkeypatch.setattr(extractor, "fetch_ranking", fake_fetch)
    monkeypatch.setattr(normalizer, "normalize_rows", lambda raw, fetched_at=None: raw)
    monkeypatch.setattr(db, "insert_results", lambda conn, rows: len(rows))
    conn = db.connect(tmp_path / "t.db")

    stats = sync.sync_all(conn, inicio="2024-01-01", fin="2024-12-31", events=[("E", "Evento")],
                          pools=("LC",), genders=("F",), categoria="X", delay=0)

    assert stats["errors"] == 0
    assert [d[3] for d in stats["skipped_days"]] == ["2024-06-06"]
    assert len(got) == 366 - 1  # todo el año salvo el día dañado
    assert "2024-06-06" not in got and "2024-06-05" in got and "2024-06-07" in got


def test_sync_con_sitio_caido_no_dispara_cientos_de_peticiones(conn, monkeypatch):
    import requests

    calls = []

    def always_500(inicio, fin, genero, categoria, prueba, piscina, session):
        calls.append(1)
        resp = requests.Response()
        resp.status_code = 500
        raise requests.HTTPError("500", response=resp)

    monkeypatch.setattr(sync.extractor, "fetch_ranking", always_500)
    stats = sync.sync_all(conn, delay=0)
    assert "errores consecutivos" in stats["aborted"]
    assert len(calls) <= sync.MAX_CONSECUTIVE_ERRORS * (2 * sync.SPLIT_BUDGET + 3)
