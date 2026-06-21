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


def test_match_swimmers_por_nombre():
    _comp, entries = programa.parse_text(HYTEK)
    swimmers = [("123", "AARON DANIEL CAMACHO"), ("456", "OTRO NADADOR")]
    stats = programa.match_swimmers(entries, swimmers)
    assert stats["matched"] == 1
    aaron = next(e for e in entries if e["swimmer_name"] == "Aaron Daniel Camacho")
    assert aaron["swimmer_id"] == "123"
