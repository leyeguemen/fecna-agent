"""Pruebas del parser del programa de campeonatos (ambos formatos)."""

from fecna_agent import programa

HYTEK = """\
Federacion Colombiana de Natacion HY-TEK's MEET MANAGER 8.0
2026 CAMPEONATO NACIONAL INFANTIL INTERCLUBES - 5/06/2026 to 7/06/2026
Event 14 Men 11 Year Olds 100 LC Meter Freestyle
Lane Name Age Team Seed Time
Heat 2 of 2 Finals Starts at 09:59 AM
0 Aaron Daniel Camacho 11 CFEN 1:15.69
4 Angel David Caballero Pinzon 11 AQUS 1:10.51
Event 1 Women 10 Year Olds 200 LC Meter IM
Lane Name Age Team Seed Time
Heat 1 of 2 Finals Starts at 08:30 AM
3 Luciana Sanchez Gutierrez 10 CDDQ 3:36.22
Event 25 Mixed 10 Year Olds 200 LC Meter Medley Relay
Lane Team Relay Seed Time
Heat 1 of 1 Finals Starts at 10:32 AM
4 DOM X12 A 5:13.62
"""

COLOMBIA = """\
LIGA VALLECAUCANA DE NATACION
XLIII Ciudad De Cali - Olga Lucia De Angulo - Infantiles
Session: 1 2026-Mar-25 Warm Up: 16:45 Start Competition: 17:45
67 (M) 11Y - 12Y - 13Y | M
400m Libre/400m Free
 R1:03:47.84
Heat # 1 ~ 17:45
3 11M Ian David Rivera Martinez ocea 7:02.39
4 11M Emiliano Alvarez Rangel mex 6:51.45
Heat # 2 ~ 17:53
1 11M Pavel Dueñas Salinas cofv 6:10.01
Program generated from the Web Service sistemas@ColombiaAcuatica.com
"""

COLOMBIA_CODIGOS = """\
TUSNAMI ENDURANCE TEAM
Chequeo Departamental de Natación
Session: 1 2026-Jun-27 Warm Up: 07:00 Start Competition: 08:00
1 (F) INF AB 10Y-13Y | F
50m Pecho/50m Breast
Heat # 1
1 Iaf Dulce Maria Gonzales Gonzales accv 1:05.36
2 Ibf Gabriela Camacho Linares accv 56.56
2 (M) INF AB 10Y-13Y | M
50m Pecho/50m Breast
Heat # 4
1 Iam Juan Jose Villota Melo navv 51.32
2 Ibm Cristobal Castrillon Aguirre estv 50.37
"""


def test_detecta_formato():
    assert programa.detect_format(HYTEK) == "hytek"
    assert programa.detect_format(COLOMBIA) == "colombia"


def test_seed_to_ms():
    assert programa.seed_to_ms("1:15.69") == 75690
    assert programa.seed_to_ms("48.12") == 48120
    assert programa.seed_to_ms("NT") is None
    assert programa.seed_to_ms("n.t.") is None


def test_hytek_parsea_inscripciones_y_omite_relevos():
    comp, entries = programa.parse_text(HYTEK)
    assert comp["source_format"] == "hytek"
    assert comp["pool_type"] == "LC"
    assert "CAMPEONATO NACIONAL" in comp["name"]
    # Tres entradas individuales; el relevo (Event 25) se omite.
    assert len(entries) == 3
    aaron = next(e for e in entries if e["swimmer_name"] == "Aaron Daniel Camacho")
    assert aaron["club_code"] == "CFEN"
    assert aaron["distance"] == 100
    assert aaron["stroke"] == "libre"
    assert aaron["gender"] == "M"
    assert aaron["start_time"] == "09:59"
    assert aaron["lane"] == 0
    assert aaron["seed_ms"] == 75690
    im = next(e for e in entries if e["swimmer_name"] == "Luciana Sanchez Gutierrez")
    assert im["stroke"] == "combinado"
    assert im["gender"] == "F"


def test_colombia_parsea_jornada_hora_y_club():
    comp, entries = programa.parse_text(COLOMBIA)
    assert comp["source_format"] == "colombia"
    assert "LIGA VALLECAUCANA" in comp["name"]
    assert len(entries) == 3
    ian = next(e for e in entries if e["swimmer_name"] == "Ian David Rivera Martinez")
    assert ian["club_code"] == "ocea"
    assert ian["distance"] == 400
    assert ian["stroke"] == "libre"
    assert ian["gender"] == "M"
    assert ian["session_date"] == "2026-03-25"
    assert ian["start_time"] == "17:45"
    assert ian["heat"] == 1
    pavel = next(e for e in entries if e["swimmer_name"] == "Pavel Dueñas Salinas")
    assert pavel["heat"] == 2
    assert pavel["start_time"] == "17:53"


def test_colombia_parsea_variante_con_codigos_de_categoria():
    comp, entries = programa.parse_text(COLOMBIA_CODIGOS)
    assert comp["source_format"] == "colombia"
    assert comp["name"] == "TUSNAMI ENDURANCE TEAM"
    assert len(entries) == 4
    villota = next(e for e in entries if e["swimmer_name"] == "Juan Jose Villota Melo")
    assert villota["event_number"] == 2
    assert villota["event_label"] == "50 Pecho"
    assert villota["heat"] == 4
    assert villota["start_time"] is None
    assert villota["club_code"] == "navv"
    assert villota["age"] is None
    assert villota["seed_raw"] == "51.32"


def test_fingerprint_estable_e_independiente_del_orden():
    comp, entries = programa.parse_text(HYTEK)
    h1 = programa.fingerprint(comp, entries)
    h2 = programa.fingerprint(comp, list(reversed(entries)))
    assert h1 == h2  # no depende del orden
    # un cambio en una inscripción cambia la huella
    entries[0]["lane"] = 9
    assert programa.fingerprint(comp, entries) != h1


def test_save_competition_solo_actualiza_si_hay_cambios():
    from fecna_agent import db

    conn = db.connect(":memory:")
    comp, entries = programa.parse_text(HYTEK)

    r1 = db.save_competition(conn, comp, entries)
    assert r1["status"] == "created"

    # recargar el mismo programa: sin cambios
    _comp2, entries2 = programa.parse_text(HYTEK)
    r2 = db.save_competition(conn, comp, entries2)
    assert r2["status"] == "unchanged"
    assert r2["competition_id"] == r1["competition_id"]

    # con un cambio real: se actualiza
    entries2[0]["start_time"] = "10:30"
    r3 = db.save_competition(conn, comp, entries2)
    assert r3["status"] == "updated"
    assert len(db.list_competitions(conn)) == 1  # no duplica


def test_alertas_quedan_aisladas_por_usuario():
    from fecna_agent import db

    conn = db.connect(":memory:")
    comp, entries = programa.parse_text(HYTEK)
    result = db.save_competition(conn, comp, entries)
    comp_id = result["competition_id"]

    db.set_watched(conn, comp_id, ["Aaron Daniel Camacho"], user_id=1)
    db.set_watched(conn, comp_id, ["Luciana Sanchez Gutierrez"], user_id=2)

    assert db.list_watched(conn, comp_id, user_id=1) == ["Aaron Daniel Camacho"]
    assert db.list_watched(conn, comp_id, user_id=2) == ["Luciana Sanchez Gutierrez"]

    rows_1 = db.watched_schedule(conn, comp_id, user_id=1)
    rows_2 = db.watched_schedule(conn, comp_id, user_id=2)
    assert {r["swimmer_name"] for r in rows_1} == {"Aaron Daniel Camacho"}
    assert {r["swimmer_name"] for r in rows_2} == {"Luciana Sanchez Gutierrez"}

    entry = db.watched_entry(conn, rows_1[0]["id"], user_id=1)
    assert entry["swimmer_name"] == "Aaron Daniel Camacho"
    assert entry["competition_name"] == comp["name"]
    assert db.watched_entry(conn, rows_1[0]["id"], user_id=2) is None


def test_migra_alertas_anteriores_a_modo_local(tmp_path):
    import sqlite3

    from fecna_agent import db

    path = tmp_path / "old.db"
    raw = sqlite3.connect(path)
    raw.executescript(
        """
        CREATE TABLE competition_watch (
          competition_id INTEGER NOT NULL,
          swimmer_name TEXT NOT NULL,
          PRIMARY KEY (competition_id, swimmer_name)
        );
        INSERT INTO competition_watch (competition_id, swimmer_name)
        VALUES (7, 'Nadador Antiguo');
        """
    )
    raw.close()

    conn = db.connect(path)
    rows = conn.execute(
        "SELECT user_id, competition_id, swimmer_name FROM competition_watch"
    ).fetchall()
    assert [(r["user_id"], r["competition_id"], r["swimmer_name"]) for r in rows] == [
        (0, 7, "Nadador Antiguo")
    ]


def _char(t, x):
    return {"text": t, "x0": x, "x1": x + 5}


def test_chars_to_line_reconstruye_espacios_por_posicion():
    chars = [
        {"text": "5", "x0": 0, "x1": 5},
        {"text": "1", "x0": 14, "x1": 19},
        {"text": "2", "x0": 20, "x1": 25},
        {"text": "M", "x0": 26, "x1": 31},
        {"text": "S", "x0": 40, "x1": 45},
        {"text": "a", "x0": 46, "x1": 51},
        {"text": "m", "x0": 52, "x1": 57},
        {"text": "n", "x0": 84, "x1": 89},
        {"text": "a", "x0": 90, "x1": 95},
        {"text": "v", "x0": 96, "x1": 101},
        {"text": "v", "x0": 102, "x1": 107},
        {"text": "1", "x0": 118, "x1": 123},
        {"text": ":", "x0": 124, "x1": 129},
        {"text": "0", "x0": 130, "x1": 135},
        {"text": "9", "x0": 136, "x1": 141},
        {"text": ".", "x0": 142, "x1": 147},
        {"text": "7", "x0": 148, "x1": 153},
        {"text": "6", "x0": 154, "x1": 159},
    ]
    assert programa._chars_to_line(chars) == "5 12M Sam navv 1:09.76"


def test_rebuild_line_separa_columnas_con_nombre_solapado():
    # Simula una inscripción HY-TEK donde el apellido invade la columna de la
    # edad y pdfplumber inserta un espacio espurio: "Lopez" -> "Lope z" + "10".
    bounds = (44.0, 150.0, 220.0)  # name_x, team_x, seed_x
    chars = [
        _char("0", 28),
        _char("A", 44), _char("n", 52), _char("a", 60),
        _char(" ", 70),
        _char("L", 80), _char("o", 96), _char("p", 110), _char("e", 124),
        _char(" ", 132),                       # espacio espurio antes de la edad
        _char("1", 134), _char("z", 136), _char("0", 140),  # edad 10 + 'z' overflow
        _char("C", 152), _char("L", 162), _char("U", 172),  # club
        _char("1", 222), _char(":", 226), _char("0", 230),
        _char("0", 234), _char(".", 238), _char("0", 242), _char("0", 246),
    ]
    out = programa._rebuild_line(chars, bounds)
    assert out == "0 Ana Lopez 10 CLU 1:00.00"


def test_clean_name_corrige_enie():
    assert programa._clean_name("Valentina Londonño Urrea") == "Valentina Londoño Urrea"
    assert programa._clean_name("Ana  Sofia   Canñon") == "Ana Sofia Cañon"


def test_hytek_parsea_jornada_y_fecha():
    text = (
        "2026 CAMPEONATO NACIONAL - 5/06/2026 to 7/06/2026\n"
        "Meet Program - 1 Jornada Viernes 5 de Junio Cal 07:00 Comp 08:30\n"
        "Event 14 Men 11 Year Olds 100 LC Meter Freestyle\n"
        "Lane Name Age Team Seed Time\n"
        "Heat 1 of 1 Finals Starts at 09:00 AM\n"
        "4 Pedro Perez Lopez 11 AQUS 1:10.51\n"
    )
    _comp, entries = programa.parse_text(text)
    assert entries[0]["session_no"] == 1
    assert entries[0]["session_date"] == "2026-06-05"


def test_match_swimmers_por_nombre():
    _comp, entries = programa.parse_text(HYTEK)
    swimmers = [("123", "AARON DANIEL CAMACHO"), ("456", "OTRO NADADOR")]
    stats = programa.match_swimmers(entries, swimmers)
    assert stats["matched"] == 1
    aaron = next(e for e in entries if e["swimmer_name"] == "Aaron Daniel Camacho")
    assert aaron["swimmer_id"] == "123"


def test_pdf_hytek_existente_sigue_parseando_bien():
    comp, entries = programa.parse_pdf("data/programa_prueba.pdf.pdf")
    assert comp["source_format"] == "hytek"
    assert comp["pool_type"] == "LC"
    assert len(entries) == 305
    first = entries[0]
    assert first["event_number"] == 1
    assert first["event_label"] == "200 IM"
    assert first["swimmer_name"] == "Luciana Sanchez Gutierrez"
    assert first["club_code"] == "CDDQ"
