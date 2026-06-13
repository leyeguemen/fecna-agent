"""Exportación de la tabla de rankings del nadador a PDF e imagen PNG.

El módulo es genérico: recibe los títulos, los encabezados y la matriz de
celdas ya formateadas (strings), y produce los bytes del archivo. No conoce el
modelo de datos, así que es fácil de probar.
"""

from io import BytesIO
from pathlib import Path

# Fuentes TrueType candidatas (mac, Linux); si ninguna existe se usa la de Pillow.
_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
_FONT_BOLD_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _safe_latin1(text: str) -> str:
    """Las fuentes core de fpdf2 codifican en latin-1; reemplaza lo que no entre."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def to_pdf(title_lines: list[str], header: list[str], table: list[list[str]]) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=12)
    pdf.add_page()
    usable = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(usable, 8, _safe_latin1(title_lines[0]))
    pdf.set_font("Helvetica", "", 10)
    for line in title_lines[1:]:
        pdf.multi_cell(usable, 6, _safe_latin1(line))
    pdf.ln(2)

    widths = _content_widths(pdf, header, table, usable)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    for name, width in zip(header, widths):
        pdf.cell(width, 8, _safe_latin1(name), border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for row in table:
        for value, width in zip(row, widths):
            pdf.cell(width, 7, _safe_latin1(value), border=1)
        pdf.ln()

    out = pdf.output()
    return bytes(out)


def _content_widths(pdf, header, table, usable, pad=4.0, min_w=12.0):
    """Ancho de cada columna según su contenido más ancho; si la suma excede el
    ancho disponible, se reduce todo proporcionalmente para que quepa."""
    pdf.set_font("Helvetica", "", 10)
    widths = []
    for i, name in enumerate(header):
        widest = pdf.get_string_width(_safe_latin1(name))
        for row in table:
            widest = max(widest, pdf.get_string_width(_safe_latin1(str(row[i]))))
        widths.append(max(min_w, widest + pad))
    total = sum(widths)
    if total > usable:
        widths = [w * usable / total for w in widths]
    return widths


def to_png(
    title_lines: list[str],
    header: list[str],
    table: list[list[str]],
    scale: int = 2,
) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    font = _load_font(_FONT_CANDIDATES, 15 * scale)
    font_bold = _load_font(_FONT_BOLD_CANDIDATES, 15 * scale)
    font_title = _load_font(_FONT_BOLD_CANDIDATES, 20 * scale)

    pad = 10 * scale
    row_h = 26 * scale
    probe = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(probe)

    # Ancho de cada columna: el máximo entre encabezado y celdas, con holgura.
    n = len(header)
    col_w = []
    for i in range(n):
        cells = [header[i]] + [str(r[i]) for r in table]
        widest = max(_text_w(draw, c, font_bold) for c in cells)
        col_w.append(widest + 2 * pad)

    table_w = sum(col_w)
    title_h = sum(_text_h(draw, line, font_title if i == 0 else font) + 4 * scale
                  for i, line in enumerate(title_lines)) + pad
    width = int(table_w + 2 * pad)
    height = int(title_h + row_h * (len(table) + 1) + 2 * pad)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    y = pad
    for i, line in enumerate(title_lines):
        f = font_title if i == 0 else font
        draw.text((pad, y), line, fill=(20, 20, 20), font=f)
        y += _text_h(draw, line, f) + 4 * scale
    y += pad // 2

    # Encabezado
    x = pad
    draw.rectangle([x, y, x + table_w, y + row_h], fill=(230, 230, 230))
    for i, name in enumerate(header):
        draw.text((x + pad, y + row_h // 4), name, fill=(0, 0, 0), font=font_bold)
        x += col_w[i]

    # Filas
    for r, row in enumerate(table):
        ry = y + row_h * (r + 1)
        if r % 2 == 1:
            draw.rectangle([pad, ry, pad + table_w, ry + row_h], fill=(247, 247, 247))
        x = pad
        for i, value in enumerate(row):
            draw.text((x + pad, ry + row_h // 4), str(value), fill=(30, 30, 30), font=font)
            x += col_w[i]

    # Líneas de la cuadrícula
    bottom = y + row_h * (len(table) + 1)
    x = pad
    for w in col_w + [0]:
        draw.line([x, y, x, bottom], fill=(210, 210, 210))
        x += w
    for r in range(len(table) + 2):
        ly = y + row_h * r
        draw.line([pad, ly, pad + table_w, ly], fill=(210, 210, 210))

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _load_font(candidates: list[str], size: int):
    from PIL import ImageFont

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def _text_w(draw, text: str, font) -> float:
    box = draw.textbbox((0, 0), str(text), font=font)
    return box[2] - box[0]


def _text_h(draw, text: str, font) -> float:
    box = draw.textbbox((0, 0), str(text), font=font)
    return box[3] - box[1]
