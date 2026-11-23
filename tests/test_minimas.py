"""Marcas mínimas: lectura de tiempos, categorías, datos del reglamento y comparación."""

import pytest

from fecna_agent import minimas


def test_tiempos_ida_y_vuelta():
    assert minimas.parse_time("00:24,71") == 24710
    assert minimas.parse_time("1:58,85") == 118850
    assert minimas.parse_time("18:10,19") == 1090190
    assert minimas.format_time(118850) == "01:58,85"
    assert minimas.format_diff(340) == "0,34 s"
    with pytest.raises(ValueError):
        minimas.parse_time("abc")


def test_categoria_por_edad():
    assert minimas.category_for("infantiles", 11) == "11"
    assert minimas.category_for("infantiles", 14) is None
    assert minimas.category_for("interligas", 13) is None
    assert [minimas.category_for("interclubes", a) for a in (14, 15, 16, 17, 18, 20, 21, 35)] == [
        "14", "15", "juvb", "juvb", "junior", "junior", "mayores", "mayores"]
    assert minimas.category_for("interligas", None) is None


def test_datos_del_reglamento_completos():
    data = minimas.reglamento_2026()
    # Interligas e interclubes: 17 pruebas x 5 categorias x 2 generos = 170 cada uno.
    assert sum(1 for d in data if d[0] == "interligas") == 170
    assert sum(1 for d in data if d[0] == "interclubes") == 170
    get = lambda *k: next(d[4] for d in data if d[:4] == k)
    assert get("interligas", "juvb", "M", "2") == 25550          # 50 L Juv B masculino
    assert get("interligas", "14", "F", "2") == 30470            # 50 L 14 años femenino
    assert get("infantiles", "10", "F", "2") == 38760
    assert get("infantiles", "13", "M", "22") == 376880          # 400 CI 13 años masculino
    assert get("interclubes", "mayores", "F", "7") == 1210210    # 1500 L mayores femenino


def test_evaluar_cumple_falta_y_sin_marca():
    res = minimas.evaluate({"2": 25550, "3": 55600, "4": 123710}, {"2": 25120, "3": 55940})
    by = {r["event"]: r for r in res["rows"]}
    assert by["50 L"]["status"] == "cumple" and by["50 L"]["diff"] == "0,43 s"
    assert by["100 L"]["status"] == "falta" and by["100 L"]["diff"] == "0,34 s"
    assert by["200 L"]["status"] == "sin_marca" and by["200 L"]["best"] is None
    assert (res["met"], res["total"]) == (1, 3)
