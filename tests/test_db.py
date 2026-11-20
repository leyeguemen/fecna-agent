import pytest

from fecna_agent import db as database


def make_row(**overrides):
    row = {
        "source": "fecna_ranking",
        "ranking_position": 1,
        "swimmer_id": "1105388915",
        "swimmer_name": "NADADOR A",
        "first_name": "NADADOR",
        "last_name": "A",
        "gender": "M",
        "birth_date": "2014-08-03",
        "birth_year_month": "2014-08",
        "event_id": "2",
        "event_name": "50m Libre/50m Free",
        "pool_type": "LC",
        "time_raw": "00:00:28.84",
        "time_ms": 28840,
        "points": 381,
        "result_date": "2026-03-25",
        "league": "COLOMBIA",
        "club": "COLOMBIA",
        "fetched_at": "2026-06-12T00:00:00+00:00",
    }
    row.update(overrides)
    return row


@pytest.fixture
def conn():
    conn = database.connect(":memory:")
    yield conn
    conn.close()


def test_insert_ignora_duplicados(conn):
    row = make_row()
    assert database.insert_results(conn, [row, row]) == 1
    assert database.insert_results(conn, [row]) == 0


def test_best_time_devuelve_menor_tiempo(conn):
    database.insert_results(conn, [
        make_row(time_ms=29500, time_raw="00:00:29.50", result_date="2025-01-01"),
        make_row(time_ms=28840, time_raw="00:00:28.84"),
    ])
    best = database.best_time(conn, "1105388915", event_id="2", pool_type="LC")
    assert best["time_ms"] == 28840


def test_compare_calcula_diferencia(conn):
    database.insert_results(conn, [
        make_row(),
        make_row(swimmer_id="1094060609", swimmer_name="NADADOR B",
                 time_ms=29680, time_raw="00:00:29.68"),
    ])
    result = database.compare_swimmers(conn, "1105388915", "1094060609", "2", "LC")
    assert result["diff_ms"] == 840  # 0.84 segundos, como en el spec


def test_ranking_una_fila_por_nadador_ordenada(conn):
    database.insert_results(conn, [
        make_row(time_ms=29500, time_raw="00:00:29.50", result_date="2025-01-01"),
        make_row(),
        make_row(swimmer_id="1094060609", swimmer_name="NADADOR B",
                 time_ms=29680, time_raw="00:00:29.68"),
    ])
    rows = database.ranking(conn, event_id="2", pool_type="LC", gender="M")
    assert [r["swimmer_id"] for r in rows] == ["1105388915", "1094060609"]
    assert rows[0]["time_ms"] == 28840


def test_list_events_distintos(conn):
    database.insert_results(conn, [
        make_row(),
        make_row(time_ms=29500, time_raw="00:00:29.50", result_date="2025-01-01"),
        make_row(event_id="6", event_name="800m Libre/800m Free",
                 time_ms=605130, time_raw="00:10:05.13"),
    ])
    assert database.list_events(conn) == [
        ("2", "50m Libre/50m Free"), ("6", "800m Libre/800m Free"),
    ]


def test_ranking_filtra_por_liga_y_categoria(conn):
    database.insert_results(conn, [
        make_row(),  # VALLE no: league=COLOMBIA, nacido 2014, resultado 2026 → 12 años
        make_row(swimmer_id="1094060609", swimmer_name="NADADOR B", league="VALLE",
                 time_ms=29680, time_raw="00:00:29.68"),
        make_row(swimmer_id="1099999999", swimmer_name="NADADOR C", league="VALLE",
                 birth_date="2012-05-01", time_ms=27000, time_raw="00:00:27.00"),
    ])
    por_liga = database.ranking(conn, "2", league="VALLE")
    assert [r["swimmer_name"] for r in por_liga] == ["NADADOR C", "NADADOR B"]

    doce_anios = database.ranking(conn, "2", age_range=(12, 12), date_to="2026-12-31")
    assert [r["swimmer_name"] for r in doce_anios] == ["NADADOR A", "NADADOR B"]

    combinado = database.ranking(conn, "2", league="VALLE", age_range=(12, 12),
                                 date_to="2026-12-31")
    assert [r["swimmer_name"] for r in combinado] == ["NADADOR B"]


def test_categoria_por_anio_de_nacimiento_no_por_fecha_del_resultado(conn):
    # Nacido en 2013 con marca de 2025 (nadada con 12 años cumplidos):
    # para una consulta con referencia 2026 su categoría es 13 AÑOS.
    database.insert_results(conn, [
        make_row(birth_date="2013-04-10", result_date="2025-10-01"),
    ])
    doce = database.ranking(conn, "2", age_range=(12, 12), date_to="2026-12-31")
    assert doce == []
    trece = database.ranking(conn, "2", age_range=(13, 13), date_to="2026-12-31")
    assert len(trece) == 1
    # Consultando la temporada 2025, sí era categoría 12 AÑOS
    doce_2025 = database.ranking(conn, "2", age_range=(12, 12), date_to="2025-12-31")
    assert len(doce_2025) == 1


def test_ranking_filtra_por_rango_de_fechas(conn):
    database.insert_results(conn, [
        make_row(time_ms=29500, time_raw="00:00:29.50", result_date="2025-01-15"),
        make_row(),  # 28840 el 2026-03-25: fuera del rango consultado
    ])
    rows = database.ranking(conn, "2", date_from="2025-01-01", date_to="2025-12-31")
    assert len(rows) == 1
    assert rows[0]["time_ms"] == 29500  # la mejor marca DENTRO del rango


def test_list_swimmers_filtra_por_liga_y_categoria(conn):
    database.insert_results(conn, [
        make_row(),
        make_row(swimmer_id="1094060609", swimmer_name="NADADOR B", league="VALLE",
                 time_ms=29680, time_raw="00:00:29.68"),
        make_row(swimmer_id="1099999999", swimmer_name="NADADOR C", league="VALLE",
                 birth_date="2012-05-01", time_ms=27000, time_raw="00:00:27.00"),
    ])
    assert len(database.list_swimmers(conn)) == 3
    valle = database.list_swimmers(conn, league="VALLE")
    assert [name for _, name in valle] == ["NADADOR B", "NADADOR C"]
    doce = database.list_swimmers(conn, league="VALLE", age_range=(12, 12),
                                  reference_year=2026)
    assert [name for _, name in doce] == ["NADADOR B"]


def test_swimmer_event_ranks_liga_y_nacional(conn):
    # Evento 2 LC M: el objetivo (A, liga VALLE) compite contra X (VALLE, más
    # rápido), Y y Z (ANTIOQUIA, Z el más rápido), y una mujer F (no debe
    # contar en el ranking masculino).
    database.insert_results(conn, [
        make_row(league="VALLE"),  # A: 28840
        make_row(swimmer_id="X1", swimmer_name="X", league="VALLE",
                 time_ms=27000, time_raw="00:00:27.00"),
        make_row(swimmer_id="Y1", swimmer_name="Y", league="ANTIOQUIA",
                 time_ms=29000, time_raw="00:00:29.00"),
        make_row(swimmer_id="Z1", swimmer_name="Z", league="ANTIOQUIA",
                 time_ms=26000, time_raw="00:00:26.00"),
        make_row(swimmer_id="F1", swimmer_name="F", gender="F", league="VALLE",
                 time_ms=20000, time_raw="00:00:20.00"),
    ])
    rows = database.swimmer_event_ranks(conn, "1105388915", date_to="2026-12-31")
    assert len(rows) == 1
    r = rows[0]
    assert r["league"] == "VALLE"
    assert r["age"] == 12  # 2026 - 2014
    assert (r["national_rank"], r["national_total"]) == (3, 4)  # Z, X, A, Y
    assert (r["league_rank"], r["league_total"]) == (2, 2)      # X, A


def test_swimmer_event_ranks_solo_cuenta_misma_categoria(conn):
    # Un nadador de otra categoría (mayor, más rápido) no debe afectar el
    # ranking del objetivo, que es categoría 12 años (nacido 2014).
    database.insert_results(conn, [
        make_row(league="VALLE"),  # objetivo, 2014, 28840
        make_row(swimmer_id="W1", swimmer_name="W", league="VALLE",
                 birth_date="2010-01-01", time_ms=20000, time_raw="00:00:20.00"),
    ])
    rows = database.swimmer_event_ranks(conn, "1105388915", date_to="2026-12-31")
    assert rows[0]["age"] == 12
    # W (16 años) está en otra categoría: el objetivo queda solo y primero
    assert (rows[0]["national_rank"], rows[0]["national_total"]) == (1, 1)


def test_swimmer_event_ranks_usa_mejor_marca(conn):
    # Dos marcas del mismo nadador en el evento: cuenta la mejor para el puesto.
    database.insert_results(conn, [
        make_row(time_ms=29500, time_raw="00:00:29.50", result_date="2025-01-01"),
        make_row(time_ms=28840, time_raw="00:00:28.84"),
        make_row(swimmer_id="X1", swimmer_name="X", time_ms=29000,
                 time_raw="00:00:29.00"),
    ])
    rows = database.swimmer_event_ranks(conn, "1105388915", date_to="2026-12-31")
    assert rows[0]["best_ms"] == 28840
    assert rows[0]["national_rank"] == 1  # 28.84 < 29.00 de X


def test_list_swimmers_detailed_incluye_club_y_liga_reciente(conn):
    database.insert_results(conn, [
        make_row(league="VALLE", club="VIEJO", result_date="2025-01-01"),
        make_row(league="VALLE", club="NAVEGANTES", result_date="2026-03-25",
                 time_ms=29000, time_raw="00:00:29.00"),
        make_row(swimmer_id="1094060609", swimmer_name="NADADOR B",
                 league="ANTIOQUIA", club="COMFENALCO", time_ms=29680,
                 time_raw="00:00:29.68"),
    ])
    detailed = database.list_swimmers_detailed(conn)
    by_id = {s[0]: s for s in detailed}
    # (swimmer_id, swimmer_name, club, league); el club es el más reciente.
    assert by_id["1105388915"] == ("1105388915", "NADADOR A", "NAVEGANTES", "VALLE")
    assert by_id["1094060609"][2:] == ("COMFENALCO", "ANTIOQUIA")


def test_swimmer_profile_top5_y_datos_personales(conn):
    # El objetivo (A, VALLE / DELFINES, nacido 2014 → 12 años al 2026) nada 6
    # pruebas; en cada una agregamos k competidores más rápidos de su misma
    # categoría y género, así su puesto nacional es k+1.
    rows, eventos = [], ["2", "6", "7", "8", "9", "10"]
    for k, ev in enumerate(eventos):
        rows.append(make_row(event_id=ev, event_name=f"E{ev}",
                             league="VALLE", club="DELFINES"))
        for j in range(k):
            rows.append(make_row(
                swimmer_id=f"{ev}_c{j}", swimmer_name=f"C{ev}{j}",
                event_id=ev, event_name=f"E{ev}", league="ANTIOQUIA", club="OTRO",
                time_ms=28840 - (j + 1) * 100, time_raw="00:00:28.00"))
    database.insert_results(conn, rows)

    profile = database.swimmer_profile(conn, "1105388915", date_to="2026-12-31")
    assert profile["swimmer_name"] == "NADADOR A"
    assert profile["league"] == "VALLE"
    assert profile["club"] == "DELFINES"
    assert profile["age"] == 12
    assert profile["gender"] == "M"
    assert profile["birth_date"] == "2014-08-03"

    top = profile["top_events"]
    assert len(top) == 5  # excluye la prueba donde queda 6º
    assert [t["national_rank"] for t in top] == [1, 2, 3, 4, 5]
    assert [t["event_id"] for t in top] == ["2", "6", "7", "8", "9"]

    # El selector de piscina acota las pruebas consideradas.
    solo_sc = database.swimmer_profile(conn, "1105388915", pool_type="SC",
                                       date_to="2026-12-31")
    assert solo_sc["top_events"] == []
    assert solo_sc["swimmer_name"] == "NADADOR A"  # los datos personales se mantienen

    assert database.swimmer_profile(conn, "NO_EXISTE", date_to="2026-12-31") is None


def test_export_anonymized_oculta_id_y_fecha(conn, tmp_path):
    database.insert_results(conn, [make_row()])  # id 1105388915, nac 2014-08-03
    dest = tmp_path / "pub.db"
    assert database.export_anonymized(conn, dest) == 1

    pub = database.connect(dest)
    row = pub.execute(
        "SELECT swimmer_id, birth_date, swimmer_name, time_raw FROM ranking_results"
    ).fetchone()
    assert row["swimmer_id"] == database.pseudonym("1105388915")  # pseudónimo estable
    assert not row["swimmer_id"].isdigit()                        # no es cédula
    assert row["birth_date"] == "2014-01-01"                      # solo el año
    assert row["swimmer_name"] == "NADADOR A"                     # nombre se conserva
    assert row["time_raw"] == "00:00:28.84"                       # tiempo se conserva

    # La categoría sigue funcionando sobre la base anonimizada (usa el año).
    ranks = database.swimmer_event_ranks(pub, database.pseudonym("1105388915"),
                                         date_to="2026-12-31")
    assert ranks[0]["age"] == 12
    pub.close()


def test_history_ordenada_por_fecha(conn):
    database.insert_results(conn, [
        make_row(),
        make_row(time_ms=29500, time_raw="00:00:29.50", result_date="2025-01-01"),
    ])
    rows = database.history(conn, "1105388915", event_id="2")
    assert [r["result_date"] for r in rows] == ["2025-01-01", "2026-03-25"]


def test_best_y_history_filtran_por_fechas(conn):
    database.insert_results(conn, [
        make_row(),  # 28840 el 2026-03-25
        make_row(time_ms=29500, time_raw="00:00:29.50", result_date="2025-01-01"),
    ])
    best_2025 = database.best_time(conn, "1105388915", "2",
                                   date_from="2025-01-01", date_to="2025-12-31")
    assert best_2025["time_ms"] == 29500  # la mejor DENTRO del rango

    rows = database.history(conn, "1105388915", event_id="2", date_to="2025-12-31")
    assert [r["result_date"] for r in rows] == ["2025-01-01"]

    result = database.compare_swimmers(conn, "1105388915", "1105388915", "2",
                                       date_from="2026-01-01")
    assert result["a"]["time_ms"] == 28840
