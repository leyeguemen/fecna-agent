import pytest

from fecna_agent import ficha


def ev(**o):
    base = {
        "event_name": "50m Libre/50m Free", "pool_type": "LC", "best_ms": 30000,
        "national_rank": 5, "national_total": 18,
        "league_rank": 3, "league_total": 5, "league": "VALLE",
    }
    base.update(o)
    return base


def make_profile(top):
    return {
        "swimmer_id": "1080063221", "swimmer_name": "SAMUEL GUERRERO BLANDON",
        "gender": "M", "age": 12, "league": "VALLE", "club": "NAVEGANTES DEL VALLE",
        "birth_date": "2014-05-10", "reference_year": 2026, "top_events": top,
    }


def test_pretty_time_quita_ceros_a_la_izquierda():
    assert ficha.pretty_time(183320) == "3:03.32"   # 3 min 3.32 s
    assert ficha.pretty_time(67510) == "1:07.51"
    assert ficha.pretty_time(27840) == "27.84"


def test_derive_highlights_mejor_nacional_y_podios_de_liga():
    top = [
        ev(event_name="200m Mariposa/200m Fly", national_rank=5, national_total=18,
           league_rank=3, league_total=5),
        ev(event_name="100m Libre/100m Free", national_rank=7, national_total=161,
           league_rank=2, league_total=35),
        ev(event_name="800m Libre/800m Free", national_rank=7, national_total=36,
           league_rank=2, league_total=7),
    ]
    h = ficha.derive_highlights(make_profile(top))
    assert h["best_national"]["event_name"].startswith("200m Mariposa")
    assert h["national_tier"] == 5           # rank 5 → TOP 5
    assert len(h["league_silver"]) == 2      # dos subcampeonatos de liga
    assert len(h["league_bronze"]) == 1


def test_render_html_incluye_datos_y_assets():
    html = ficha.render_html(
        make_profile([ev()]),
        photo_data_uri="data:image/png;base64,AAA",
        logo_data_uri="data:image/png;base64,BBB",
        championship="CAMPEONATO NACIONAL 2026", venue="IBAGUE",
    )
    assert "<html" in html.lower()
    assert "SAMUEL GUERRERO BLANDON" in html
    assert "NAVEGANTES DEL VALLE" in html
    assert "data:image/png;base64,AAA" in html   # foto embebida
    assert "data:image/png;base64,BBB" in html   # logo embebido
    assert "CAMPEONATO NACIONAL 2026" in html


def test_render_html_sin_assets_no_falla():
    html = ficha.render_html(make_profile([ev()]))
    assert "SAMUEL GUERRERO BLANDON" in html
    assert "data:image" not in html  # sin foto/logo no se inserta ninguna


def _browser_disponible() -> bool:
    try:
        import pathlib

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return pathlib.Path(p.chromium.executable_path).exists()
    except Exception:
        return False


@pytest.mark.skipif(not _browser_disponible(),
                    reason="Playwright/Chromium no disponible")
def test_render_png_y_pdf_de_la_ficha():
    html = ficha.render_html(make_profile([ev()]))
    png = ficha.render_png(html)
    pdf = ficha.render_pdf(html)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"   # firma PNG
    assert pdf[:5] == b"%PDF-"               # firma PDF
    assert len(png) > 1000 and len(pdf) > 1000
