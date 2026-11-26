"""Tarjeta de mínimas del Inicio: muestra la mejor marca cumplida (issue #8)."""

from api.routers import me, minimas as minimas_router


def _r(event, best, minima, status):
    diff = abs(minima - best)
    return {"event": event, "best_ms": best, "minima_ms": minima, "best": str(best), "minima": str(minima),
            "status": status, "diff_ms": diff, "diff": f"{diff} ms"}


def _home(monkeypatch, rows):
    ev = {"applicable": True, "rows": rows, "category_label": "Cat", "total": len(rows),
          "met": sum(r["status"] == "cumple" for r in rows)}
    monkeypatch.setattr(minimas_router, "evaluate_swimmer", lambda sid, t: ev)
    return me._home_minima("1")


def test_muestra_la_cumplida_con_mas_margen_relativo(monkeypatch):
    # 50 m: 1 s de 30 s (3,3 %) · 800 m: 5 s de 600 s (0,8 %) → gana el 50 m aunque el margen absoluto sea menor.
    out = _home(monkeypatch, [_r("800 L", 595000, 600000, "cumple"), _r("50 L", 29000, 30000, "cumple"),
                              _r("100 L", 61000, 60000, "falta")])
    assert out["event"] == "50 L" and out["status"] == "cumple" and out["diff"] == "1000 ms" and out["met"] == 2


def test_si_no_cumple_ninguna_muestra_la_mas_cercana(monkeypatch):
    out = _home(monkeypatch, [_r("50 L", 32000, 30000, "falta"), _r("100 L", 60500, 60000, "falta"),
                              {**_r("200 L", 0, 1, "sin_marca"), "best_ms": None, "diff_ms": None}])
    assert out["event"] == "100 L" and out["status"] == "falta"


def test_sin_marcas_no_muestra_prueba(monkeypatch):
    out = _home(monkeypatch, [{**_r("50 L", 0, 30000, "sin_marca"), "best_ms": None, "diff_ms": None}])
    assert out["event"] is None and out["status"] is None
