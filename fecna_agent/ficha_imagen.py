"""Ficha para redes: imagen PNG vertical 1080x1920 (9:16) con foto, nombre, liga, campeonato y
las mejores marcas. Se dibuja con Pillow en el servidor para que salga igual en Android, iPhone y web.

Tipografías: Space Grotesk e Inter (licencia OFL, ver assets/fonts).
"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .ficha import pretty_time, short_event

FONTS = Path(__file__).parent / "assets" / "fonts"
W, H = 1080, 1920
PHOTO_H = 600
ROW_H = 106

NAVY_DARK, NAVY, BLUE, CYAN = (2, 27, 61), (2, 62, 138), (0, 119, 182), (0, 180, 216)
LIGHT, INK, LBLUE, GRAY, SOFT = (238, 245, 251), (11, 31, 51), (0, 95, 149), (62, 86, 106), (184, 212, 230)
ACCENT, WHITE = (255, 194, 26), (255, 255, 255)

MAX_PHOTO_PIXELS = 25_000_000


def _font(file: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / file), size)


def grotesk(size):
    return _font("SpaceGrotesk_700Bold.ttf", size)


def inter(size, bold=False):
    return _font("Inter_700Bold.ttf" if bold else "Inter_600SemiBold.ttf", size)


# --------------------------------------------------------------- selección de marcas

def select_marks(rows: list[dict], ranks: dict, tournament: str | None = None, limit: int = 5) -> list[dict]:
    """Mejor marca por prueba/piscina (solo del campeonato si se indica), ordenadas por puntos.

    rows: marcas del nadador (event_id, event_name, pool_type, time_ms, points, tournament).
    ranks: {(event_id, pool): (puesto_nacional, mejor_tiempo_ms)}. El puesto solo se muestra si la
    marca es su mejor de esa prueba, porque ese es el puesto que calcula el ranking."""
    best: dict[tuple, dict] = {}
    for r in rows:
        if tournament and r.get("tournament") != tournament:
            continue
        key = (r["event_id"], r["pool_type"])
        if key not in best or r["time_ms"] < best[key]["time_ms"]:
            best[key] = r
    out = []
    for (event_id, pool), r in best.items():
        rank_info = ranks.get((event_id, pool))
        name = short_event(r["event_name"])
        distance, _, stroke = name.partition(" ")
        out.append({
            "distance": distance.replace("m", " m", 1) if distance[-1:] == "m" else distance,
            "stroke": (stroke or name) + (" · corta" if pool == "SC" else ""),
            "time": pretty_time(r["time_ms"]),
            "time_ms": r["time_ms"],
            "points": r.get("points"),
            "rank": rank_info[0] if rank_info and rank_info[1] == r["time_ms"] else None,
        })
    out.sort(key=lambda m: (-(m["points"] if m["points"] is not None else -1), m["time_ms"]))
    return out[:limit]


# ------------------------------------------------------------------ dibujo auxiliar

def _gradient(size, top, bottom) -> Image.Image:
    g = Image.linear_gradient("L").resize(size)
    return ImageOps.colorize(g, black=top, white=bottom).convert("RGB")


def _aa_ellipse(img, x, y, d, fill, outline=None, ow=0):
    """Círculo suavizado (supermuestreo x4)."""
    s = 4
    mask = Image.new("L", (d * s, d * s), 0)
    md = ImageDraw.Draw(mask)
    if outline:
        md.ellipse((0, 0, d * s - 1, d * s - 1), fill=255)
        layer = Image.new("RGB", (d, d), outline)
        img.paste(layer, (x, y), mask.resize((d, d), Image.LANCZOS))
        mask = Image.new("L", (d * s, d * s), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse((ow * s, ow * s, d * s - 1 - ow * s, d * s - 1 - ow * s), fill=255)
    else:
        md.ellipse((0, 0, d * s - 1, d * s - 1), fill=255)
    img.paste(Image.new("RGB", (d, d), fill), (x, y), mask.resize((d, d), Image.LANCZOS))


def _wrap(draw, text, font, max_w) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _fit(draw, text, make_font, max_w, start, minimum):
    size = start
    while size > minimum and draw.textlength(text, font=make_font(size)) > max_w:
        size -= 4
    return make_font(size)


def _swimmer_icon(img, cx, cy):
    d = ImageDraw.Draw(img)
    d.ellipse((cx + 3, cy - 20, cx + 15, cy - 8), outline=WHITE, width=4)
    d.line([(cx - 16, cy + 2), (cx - 2, cy - 8), (cx + 6, cy - 4), (cx + 14, cy + 4)], fill=WHITE, width=4, joint="curve")
    for dy in (12, 22):
        d.arc((cx - 22, cy + dy - 6, cx - 6, cy + dy + 6), 0, 180, fill=WHITE, width=3)
        d.arc((cx - 6, cy + dy - 6, cx + 10, cy + dy + 6), 180, 360, fill=WHITE, width=3)
        d.arc((cx + 10, cy + dy - 6, cx + 26, cy + dy + 6), 0, 180, fill=WHITE, width=3)


def _star(draw, cx, cy, r, fill):
    import math

    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def _trophy(draw, cx, cy, s, color):
    draw.polygon([(cx - s, cy - s), (cx + s, cy - s), (cx + s * 0.8, cy + s * 0.2), (cx, cy + s * 0.7), (cx - s * 0.8, cy + s * 0.2)], fill=color)
    draw.rectangle((cx - s * 0.12, cy + s * 0.6, cx + s * 0.12, cy + s * 1.1), fill=color)
    draw.rectangle((cx - s * 0.6, cy + s * 1.05, cx + s * 0.6, cy + s * 1.25), fill=color)
    draw.arc((cx - s * 1.5, cy - s * 0.9, cx - s * 0.7, cy + s * 0.1), 90, 270, fill=color, width=6)
    draw.arc((cx + s * 0.7, cy - s * 0.9, cx + s * 1.5, cy + s * 0.1), 270, 90, fill=color, width=6)


# ------------------------------------------------------------------------ la ficha

def render_png(profile: dict, marks: list[dict], tournament: str | None = None, photo: bytes | None = None) -> bytes:
    """profile: swimmer_name, first_name, last_name, age, league, club. Devuelve los bytes del PNG."""
    img = _gradient((W, H), NAVY_DARK, NAVY)
    draw = ImageDraw.Draw(img)

    # --- foto (o fondo de agua) con el nombre encima
    area = _gradient((W, PHOTO_H), BLUE, CYAN)
    if photo:
        pic = Image.open(BytesIO(photo))
        if pic.width * pic.height > MAX_PHOTO_PIXELS:
            raise ValueError("La foto es demasiado grande.")
        pic = ImageOps.exif_transpose(pic).convert("RGB")
        area = ImageOps.fit(pic, (W, PHOTO_H), Image.LANCZOS, centering=(0.5, 0.3))
    else:
        ad = ImageDraw.Draw(area, "RGBA")
        ad.ellipse((W / 2 - 80, 150, W / 2 + 80, 310), fill=(255, 255, 255, 60))
        ad.ellipse((W / 2 - 190, 330, W / 2 + 190, 700), fill=(255, 255, 255, 60))
    overlay = Image.new("RGBA", (W, PHOTO_H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    for i in range(420):
        ov.line([(0, PHOTO_H - 420 + i), (W, PHOTO_H - 420 + i)], fill=(*NAVY_DARK, int(240 * (i / 420) ** 1.3)))
    area = Image.alpha_composite(area.convert("RGBA"), overlay).convert("RGB")
    img.paste(area, (0, 0))
    draw = ImageDraw.Draw(img)

    first = (profile.get("first_name") or profile["swimmer_name"]).split()[0].upper()
    last = (profile.get("last_name") or " ".join(profile["swimmer_name"].split()[1:]) or "").split()
    last = (last[0] if last else "").upper()
    f1 = _fit(draw, first, grotesk, W - 96, 128, 64)
    f2 = _fit(draw, last or " ", grotesk, W - 96, 128, 64)
    base2 = PHOTO_H - 46
    draw.text((48, base2), last, font=f2, fill=ACCENT, anchor="ls")
    draw.text((48, base2 - int(f2.size * 0.98)), first, font=f1, fill=WHITE, anchor="ls")

    # --- escudo (club) y marca
    _aa_ellipse(img, 40, 40, 190, NAVY_DARK, outline=ACCENT, ow=7)
    club = (profile.get("club") or "").upper()
    if club:
        cf = grotesk(30)
        lines = _wrap(draw, club, cf, 130)
        while (len(lines) > 4 or max(draw.textlength(w, font=cf) for w in club.split()) > 130) and cf.size > 14:
            cf = grotesk(cf.size - 2)
            lines = _wrap(draw, club, cf, 130)
        y = 135 - len(lines) * (cf.size + 2) / 2
        for ln in lines[:4]:
            draw.text((135, y), ln, font=cf, fill=WHITE, anchor="mt")
            y += cf.size + 2
    draw.text((W - 44, 56), "NATIA", font=grotesk(52), fill=WHITE, anchor="rt")

    # --- edad y liga
    y = PHOTO_H
    band = grotesk(46)
    x = 48
    parts = []
    if profile.get("age") is not None:
        parts.append((f"{profile['age']} AÑOS", WHITE))
    if profile.get("league"):
        parts.append((f"LIGA {profile['league'].upper()}", ACCENT))
    if parts:
        draw.rectangle((0, y, W, y + 96), fill=BLUE)
    for i, (txt, col) in enumerate(parts):
        if i:
            x += 24
            draw.text((x, y + 48), "|", font=band, fill=SOFT, anchor="lm")
            x += int(draw.textlength("|", font=band)) + 24
        draw.text((x, y + 48), txt, font=band, fill=col, anchor="lm")
        x += int(draw.textlength(txt, font=band))
    if parts:
        y += 96

    # --- campeonato
    label = "CAMPEONATO" if tournament else "RESUMEN"
    title = (tournament or "Mejores marcas de su historial").upper()
    tf = grotesk(46)
    lines = _wrap(draw, title, tf, W - 96)[:3]
    block_h = 26 + 30 + 6 + len(lines) * 50 + 26
    draw.rectangle((0, y, W, y + block_h), fill=LIGHT)
    draw.text((48, y + 26 + 24), label, font=inter(26, True), fill=LBLUE, anchor="ls")
    ty = y + 26 + 30 + 6 + 40
    for ln in lines:
        draw.text((48, ty), ln, font=tf, fill=INK, anchor="ls")
        ty += 50
    y += block_h

    # --- marcas
    y += 26
    rib = "MIS 5 MEJORES MARCAS" if len(marks) >= 5 else "MIS MEJORES MARCAS"
    rf = grotesk(34)
    rw = int(draw.textlength(rib, font=rf)) + 88
    draw.rounded_rectangle((-20, y, rw, y + 62), radius=10, fill=NAVY_DARK, outline=ACCENT, width=3)
    draw.text((48, y + 31), rib, font=rf, fill=WHITE, anchor="lm")
    y += 62 + 16
    panel_h = len(marks) * ROW_H + 8
    draw.rectangle((0, y, W, y + panel_h), fill=LIGHT)
    ry = y + 4
    for i, m in enumerate(marks):
        cy = ry + ROW_H // 2
        _aa_ellipse(img, 48, cy - 36, 72, NAVY)
        _swimmer_icon(img, 84, cy)
        draw = ImageDraw.Draw(img)
        draw.text((142, cy + 2), m["distance"], font=grotesk(40), fill=INK, anchor="ls")
        draw.text((142, cy + 34), m["stroke"].upper(), font=_fit(draw, m["stroke"].upper(), lambda s: inter(s, True), 230, 26, 16), fill=LBLUE, anchor="ls")
        draw.text((394, cy + 20), m["time"], font=grotesk(56), fill=NAVY, anchor="ls")
        rank = f"{m['rank']}.º" if m["rank"] else "—"
        pts = str(m["points"]) if m["points"] is not None else "—"
        draw.text((850, cy + 4), rank, font=grotesk(40), fill=INK, anchor="ms")
        draw.text((850, cy + 32), "NAC.", font=inter(24), fill=GRAY, anchor="ms")
        draw.text((977, cy + 4), pts, font=grotesk(40), fill=NAVY, anchor="ms")
        draw.text((977, cy + 32), "PUNTOS", font=inter(24), fill=GRAY, anchor="ms")
        if i < len(marks) - 1:
            for dx in range(48, W - 48, 14):
                draw.line([(dx, ry + ROW_H - 1), (dx + 7, ry + ROW_H - 1)], fill=(157, 182, 201), width=2)
        ry += ROW_H
    y += panel_h

    # --- pie
    foot_h = 172
    foot = Image.new("RGBA", (W, foot_h), (*NAVY_DARK, 180))
    img.paste(foot, (0, H - foot_h), foot)
    draw = ImageDraw.Draw(img)
    draw.text((W / 2, H - foot_h + 48), "DISCIPLINA, ESFUERZO Y PASIÓN DENTRO Y FUERA DEL AGUA", font=grotesk(28), fill=WHITE, anchor="mm")
    small = inter(24)
    for k, ln in enumerate(_wrap(draw, "Datos del ranking público de FECNA · NATIA es una app independiente, no avalada por FECNA", small, W - 100)):
        draw.text((W / 2, H - foot_h + 92 + k * 32), ln, font=small, fill=SOFT, anchor="mt")

    # --- destacados (en el espacio que queda)
    cells = []
    ranked = [m for m in marks if m["rank"]]
    if ranked:
        b = min(ranked, key=lambda m: m["rank"])
        cells.append(("trophy", "MEJOR PUESTO", f"{b['rank']}.º lugar", f"{b['distance']} {b['stroke'].split(' ·')[0].lower()}"))
    scored = [m for m in marks if m["points"] is not None]
    if scored:
        b = max(scored, key=lambda m: m["points"])
        cells.append(("star", "MAYOR PUNTAJE", f"{b['points']} pts", f"{b['distance']} {b['stroke'].split(' ·')[0].lower()}"))
    space_top, space_bot = y, H - foot_h
    if cells and space_bot - space_top >= 130:
        cy = (space_top + space_bot) // 2
        cw = (W - 80) // len(cells)
        for i, (icon, lab, val, sub) in enumerate(cells):
            x0 = 40 + i * cw
            if icon == "trophy":
                _trophy(draw, x0 + 40, cy - 6, 22, ACCENT)
            else:
                _star(draw, x0 + 40, cy, 34, ACCENT)
            draw.text((x0 + 100, cy - 34), lab, font=inter(24, True), fill=SOFT, anchor="lm")
            draw.text((x0 + 100, cy + 6), val, font=grotesk(46), fill=ACCENT, anchor="lm")
            draw.text((x0 + 100, cy + 44), sub, font=inter(26), fill=WHITE, anchor="lm")
            if i < len(cells) - 1:
                draw.line([(x0 + cw - 10, cy - 50), (x0 + cw - 10, cy + 50)], fill=(80, 110, 150), width=2)

    out = BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()
