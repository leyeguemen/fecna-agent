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
