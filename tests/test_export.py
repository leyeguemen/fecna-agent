from io import BytesIO

from fecna_agent import export

TITLE = ["Rankings de JORGE MARIO MURILLO GALLEGO (1105388915)",
         "Liga: VALLE  ·  Categoría: 12 años (al 2026)",
         "Rango: 2024-01-01 a 2026-06-13"]
HEADER = ["Prueba", "Piscina", "Género", "Categoría", "Mejor marca",
          "Puesto liga", "Puesto Colombia"]
TABLE = [
    ["50m Libre/50m Free", "LC", "M", "12 años", "00:00:28.31", "1 / 35", "1 / 162"],
    ["200m Comb.Ind/200m Medley", "LC", "M", "12 años", "00:02:40.42", "1 / 17", "1 / 99"],
]


def test_pdf_es_un_pdf_valido():
    data = export.to_pdf(TITLE, HEADER, TABLE)
    assert isinstance(data, bytes)
    assert data[:5] == b"%PDF-"
    assert len(data) > 800


def test_png_es_una_imagen_valida():
    from PIL import Image

    data = export.to_png(TITLE, HEADER, TABLE)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    img = Image.open(BytesIO(data))
    assert img.format == "PNG"
    assert img.width > 200 and img.height > 100


def test_caracteres_fuera_de_latin1_no_rompen_el_pdf():
    # Un nombre con un carácter raro no debe abortar la exportación a PDF.
    title = ["Rankings de TEST ـ (1)", "Liga: X"]
    data = export.to_pdf(title, HEADER, TABLE)
    assert data[:5] == b"%PDF-"


def test_tabla_vacia_genera_archivos():
    assert export.to_pdf(TITLE, HEADER, [])[:5] == b"%PDF-"
    assert export.to_png(TITLE, HEADER, [])[:8] == b"\x89PNG\r\n\x1a\n"


def test_tabla_con_otras_columnas_se_exporta():
    # El exportador es genérico: ajusta el ancho al contenido, no a un esquema fijo.
    header = ["Puesto", "Tiempo", "Nadador", "F. nac.", "Club", "Liga", "Fecha"]
    table = [
        ["1", "00:00:26.00", "NOMBRE LARGO DE UN NADADOR DE PRUEBA", "2014-01-01",
         "CLUB DEPORTIVO EJEMPLO", "ANTIOQUIA", "2026-06-01"],
        ["2", "00:00:27.10", "OTRO NADADOR", "2014-05-05", "OTRO CLUB", "VALLE",
         "2026-06-02"],
    ]
    assert export.to_pdf(["Ranking de prueba"], header, table)[:5] == b"%PDF-"
    assert export.to_png(["Ranking de prueba"], header, table)[:8] == b"\x89PNG\r\n\x1a\n"
