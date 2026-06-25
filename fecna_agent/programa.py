"""Carga del programa (heat sheet) de un campeonato desde PDF.

Soporta los dos formatos habituales:
  - HY-TEK MEET MANAGER (nacionales): "Event 1 Women 10 Year Olds 200 LC Meter IM"
  - Colombia Acuática / Web Service (ligas): "67 (M) 11Y - 12Y - 13Y | M"

El objetivo es saber qué pruebas debe nadar cada deportista y a qué hora. El
parseo del texto está separado de la lectura del PDF para poder probarlo con
texto plano (parse_text); parse_pdf solo extrae el texto y delega.

El cruce con la base de datos se hace por NOMBRE normalizado: en el PDF el club
es un código de 4 letras (COMP, crpv) que no corresponde a los nombres completos
de la base, así que el nombre es la llave confiable para enriquecer con el
ranking/mejor marca de cada nadador.
"""

import hashlib
import re
import unicodedata

# --- Canónico de estilos: del texto del PDF a la palabra usada en el catálogo --
_STROKE_KEYS = {
    "combinado": ("im", "medley", "comb", "combinado", "comb.ind"),
    "libre": ("free", "freestyle", "libre", "crol"),
    "espalda": ("back", "backstroke", "espalda", "dorso"),
    "pecho": ("breast", "breaststroke", "pecho", "braza"),
    "mariposa": ("fly", "butterfly", "mariposa"),
    "relevo": ("relay", "relevo"),
}

_MESES = {
    "ene": 1, "jan": 1, "feb": 2, "mar": 3, "abr": 4, "apr": 4, "may": 5,
    "jun": 6, "jul": 7, "ago": 8, "aug": 8, "sep": 9, "oct": 10, "nov": 11,
    "dic": 12, "dec": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}


def normalize(text: str) -> str:
    """Minúsculas sin tildes (igual criterio que resolver.normalize)."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def normalize_name(name: str) -> str:
    """Clave de cruce de nadadores: mayúsculas sin tildes, espacios colapsados."""
    text = unicodedata.normalize("NFD", name.upper())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip()


def stroke_key(text: str) -> str | None:
    """Estilo canónico a partir de un fragmento de texto del PDF/catálogo."""
    low = normalize(text)
    for key, words in _STROKE_KEYS.items():
        if any(w in low for w in words):
            return key
    return None


def seed_to_ms(raw: str) -> int | None:
    """'3:36.22' → 216220; '48.12' → 48120; 'NT'/'n.t.' → None."""
    raw = raw.strip()
    if not raw or normalize(raw).replace(".", "").replace(" ", "") in ("nt",):
        return None
    if not re.match(r"^\d{0,2}:?\d{0,2}:?\d{1,2}\.\d{1,2}$", raw):
        return None
    parts = raw.split(":")
    try:
        seconds = float(parts[-1])
        minutes = int(parts[-2]) if len(parts) >= 2 else 0
        hours = int(parts[-3]) if len(parts) >= 3 else 0
    except ValueError:
        return None
    return int(round((hours * 3600 + minutes * 60 + seconds) * 1000))


def _to_24h(hhmm: str, meridian: str | None) -> str:
    """'09:04','AM' → '09:04'; '01:00','PM' → '13:00'. Sin meridiano: tal cual."""
    h, m = (int(x) for x in hhmm.split(":"))
    if meridian:
        meridian = meridian.upper()
        if meridian == "PM" and h != 12:
            h += 12
        elif meridian == "AM" and h == 12:
            h = 0
    return f"{h:02d}:{m:02d}"


# --- Detección de formato -----------------------------------------------------
def detect_format(text: str) -> str:
    low = text.lower()
    if "hy-tek" in low or "meet manager" in low or "year olds" in low:
        return "hytek"
    if "web service" in low or "colombiaacuatica" in low or re.search(r"heat\s*#", low):
        return "colombia"
    return "hytek"


# --- HY-TEK -------------------------------------------------------------------
_HY_TITLE = re.compile(r"^\d{4}\s+.+?-\s+\d.*\d{4}")
_HY_EVENT = re.compile(
    r"^Event\s+(\d+)\s+(Women|Men|Mixed)\s+(.+?)\s+(\d+)\s+(LC|SC)\s+Meter\s+(.+?)\s*$"
)
_HY_HEAT = re.compile(r"Heat\s+\d+\s+of\s+\d+.*Starts at\s+(\d{1,2}:\d{2})\s*(AM|PM)?")
_HY_ENTRY = re.compile(
    r"^(\d{1,2})\s+(.+?)\s+(\d{1,2})\s+([A-Z0-9]{2,5})\s+(NT|[\d:]*\d\.\d{2})\s*$"
)
# Encabezado de jornada (abarca todo el ancho): "... 1 Jornada Viernes 5 de Junio".
_HY_JORNADA = re.compile(r"(\d+)\s+Jornada\s+\S+\s+(\d{1,2})\s+de\s+(\w+)", re.I)
_GENDER = {"Women": "F", "Men": "M", "Mixed": "X"}


def _parse_hytek(lines: list[str]) -> tuple[dict, list[dict]]:
    competition = {"name": None, "pool_type": None, "source_format": "hytek"}
    entries: list[dict] = []
    ev: dict | None = None
    heat = start_time = None
    year = session_no = session_date = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if competition["name"] is None and _HY_TITLE.match(line):
            competition["name"] = line
            ym = re.match(r"(\d{4})", line)
            year = int(ym.group(1)) if ym else None
            continue
        m = _HY_JORNADA.search(line)
        if m:
            session_no = int(m.group(1))
            mon = _MESES.get(normalize(m.group(3)))
            if year and mon:
                session_date = f"{year}-{mon:02d}-{int(m.group(2)):02d}"
            continue
        m = _HY_EVENT.match(line)
        if m:
            num, gender, age, dist, pool, stroke = m.groups()
            competition["pool_type"] = competition["pool_type"] or pool
            ev = {
                "event_number": int(num), "gender": _GENDER.get(gender, "X"),
                "category": age.strip(), "distance": int(dist), "pool_type": pool,
                "event_label": f"{dist} {stroke.strip()}", "stroke": stroke_key(stroke),
            }
            heat = start_time = None
            continue
        m = _HY_HEAT.search(line)
        if m:
            start_time = _to_24h(m.group(1), m.group(2))
            heat = (heat or 0) + 1
            continue
        if ev and ev["stroke"] != "relevo":
            m = _HY_ENTRY.match(line)
            if m:
                lane, name, age, team, seed = m.groups()
                entry = _entry(ev, heat, start_time, lane, name, team, age, seed)
                entry["session_no"] = session_no
                entry["session_date"] = session_date
                entries.append(entry)
    return competition, entries


# --- Colombia Acuática --------------------------------------------------------
_CO_EVENT = re.compile(r"^(\d+)\s+\(([MFX])\)\s+(.+?)\s+\|\s+([MFX])\s*$")
_CO_DIST = re.compile(r"^(\d+)\s*m\s+(.+?)(?:/.*)?$")
_CO_SESSION = re.compile(r"Session:\s*(\d+)\s+(\d{4})-([A-Za-z]{3})-(\d{1,2})")
_CO_HEAT = re.compile(r"Heat\s*#\s*(\d+)\s*~\s*(\d{1,2}:\d{2})")
_CO_ENTRY = re.compile(
    r"^(\d{1,2})\s+(\d{1,2})([MF])\s+(.+?)\s+([a-z0-9&]{2,6})\s+(n\.t\.|[\d:]*\d\.\d{1,2})\s*$"
)


def _parse_colombia(lines: list[str]) -> tuple[dict, list[dict]]:
    competition = {"name": None, "pool_type": "LC", "source_format": "colombia"}
    entries: list[dict] = []
    ev: dict | None = None
    heat = start_time = session_no = session_date = None
    expect_distance = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if competition["name"] is None and "liga" in line.lower():
            competition["name"] = line
        m = _CO_SESSION.search(line)
        if m:
            session_no = int(m.group(1))
            mon = _MESES.get(m.group(3).lower(), 1)
            session_date = f"{m.group(2)}-{mon:02d}-{int(m.group(4)):02d}"
            continue
        m = _CO_EVENT.match(line)
        if m:
            num, _g1, age, gender = m.groups()
            ev = {
                "event_number": int(num), "gender": gender, "category": age.strip(),
                "distance": None, "pool_type": "LC", "event_label": None, "stroke": None,
            }
            expect_distance = True
            heat = start_time = None
            continue
        if expect_distance:
            m = _CO_DIST.match(line)
            if m:
                ev["distance"] = int(m.group(1))
                ev["event_label"] = f"{m.group(1)} {m.group(2).strip()}"
                ev["stroke"] = stroke_key(m.group(2))
                expect_distance = False
            continue
        m = _CO_HEAT.search(line)
        if m:
            heat = int(m.group(1))
            start_time = _to_24h(m.group(2), None)
            continue
        if ev and ev.get("stroke") and ev["stroke"] != "relevo":
            m = _CO_ENTRY.match(line)
            if m:
                lane, age, _g, name, club, seed = m.groups()
                entry = _entry(ev, heat, start_time, lane, name, club, age, seed)
                entry["session_no"] = session_no
                entry["session_date"] = session_date
                entries.append(entry)
    return competition, entries


def _clean_name(name: str) -> str:
    """Normaliza espacios y corrige la 'ñ' que el PDF extrae como 'nñ'."""
    name = name.replace("nñ", "ñ").replace("Nñ", "Ñ")
    return re.sub(r"\s+", " ", name).strip()


def _entry(ev, heat, start_time, lane, name, club, age, seed) -> dict:
    return {
        "event_number": ev["event_number"], "event_label": ev["event_label"],
        "event_id": None, "distance": ev["distance"], "stroke": ev["stroke"],
        "gender": ev["gender"], "category": ev["category"],
        "session_no": None, "session_date": None,
        "heat": heat, "lane": int(lane), "start_time": start_time,
        "swimmer_name": _clean_name(name), "club_code": club.strip(),
        "age": int(age), "seed_ms": seed_to_ms(seed), "seed_raw": seed.strip(),
        "swimmer_id": None,
    }


# --- API pública --------------------------------------------------------------
def parse_text(text: str) -> tuple[dict, list[dict]]:
    """Texto del programa → (competition, entries). Detecta el formato solo."""
    lines = text.splitlines()
    fmt = detect_format(text)
    competition, entries = (_parse_colombia if fmt == "colombia" else _parse_hytek)(lines)
    return competition, entries


def parse_pdf(source) -> tuple[dict, list[dict]]:
    """Lee un PDF (ruta o bytes/buffer) y lo parsea. Requiere pdfplumber.

    HY-TEK imprime el programa en dos columnas y los nombres largos se solapan
    con la edad; por eso ese formato se reconstruye por posición (x) de cada
    caracter en vez de confiar en el texto plano. Colombia Acuática es de una
    columna y se parsea directo del texto."""
    import pdfplumber

    with pdfplumber.open(source) as pdf:
        full = "\n".join(pg.extract_text() or "" for pg in pdf.pages)
        if detect_format(full) == "hytek":
            return _parse_hytek(_hytek_lines(pdf))
        return _parse_colombia(_colombia_lines(pdf))


# --- Reconstrucción posicional del PDF HY-TEK (dos columnas) ------------------
def _split_x(page, bin_w: int = 5) -> float | None:
    """x donde separar las dos columnas; None si la página es de una sola.

    El hueco entre columnas se ve como una franja vertical por la que pasan muy
    pocas filas (solo encabezados de ancho completo), frente a las columnas que
    tienen decenas de filas. Mide cobertura por filas (tops) en cada franja."""
    lo, hi = page.width * 0.40, page.width * 0.60
    rows_at: dict[int, set] = {}
    for c in page.chars:
        if lo <= c["x0"] <= hi:
            rows_at.setdefault(int(c["x0"] // bin_w) * bin_w, set()).add(round(c["top"]))
    if not rows_at:
        return None
    cover = {k: len(v) for k, v in rows_at.items()}
    threshold = max(3, max(cover.values()) * 0.3)
    bins = sorted(range(int(lo) // bin_w * bin_w, int(hi) + bin_w, bin_w))
    best_run, run = (0, None), []
    for b in bins:
        if cover.get(b, 0) <= threshold:
            run.append(b)
            if len(run) > best_run[0]:
                best_run = (len(run), run[len(run) // 2])
        else:
            run = []
    return float(best_run[1]) + bin_w / 2 if best_run[1] is not None else None


def _column_bounds(line_chars: list) -> tuple[float, float, float] | None:
    """(name_x, team_x, seed_x) del encabezado 'Lane Name Age Team Seed Time'.

    Se calcula desde la x de cada caracter (no de palabras): en el recorte por
    columna los espacios desaparecen y 'Lane Name Age' quedaría como un solo
    token, así que se localiza cada rótulo en el texto sin espacios."""
    seq = [(c["text"], c["x0"]) for c in sorted(line_chars, key=lambda c: c["x0"])
           if c["text"].strip()]
    text = "".join(t for t, _ in seq).lower()
    if not all(k in text for k in ("lane", "name", "team", "seed")):
        return None
    return seq[text.find("name")][1], seq[text.find("team")][1], seq[text.find("seed")][1]


def _rebuild_line(chars: list, bounds: tuple[float, float, float] | None) -> str:
    """Reconstruye una línea; si es inscripción, separa campos por columna (x).

    En la zona nombre/edad los dígitos son la edad y las letras son el nombre,
    aunque se solapen físicamente (caso de apellidos largos)."""
    chars = sorted(chars, key=lambda c: c["x0"])
    raw = re.sub(r"\s+", " ", "".join(c["text"] for c in chars)).strip()
    if not bounds:
        return raw
    name_x, team_x, seed_x = bounds
    # Los datos arrancan unos píxeles a la izquierda de su rótulo; los márgenes
    # evitan que el primer caracter de cada campo caiga en la columna anterior.
    lane_c, zone, team_c, seed_c = [], [], [], []
    for c in chars:
        t, x = c["text"], c["x0"]
        if x < name_x - 8:
            lane_c.append(t)
        elif x < team_x - 4:
            zone.append((t, x))  # nombre y edad solapados: se separan abajo
        elif x < seed_x - 6:
            team_c.append(t)
        else:
            seed_c.append(t)
    # En la zona nombre/edad: los dígitos son la edad; las letras son el nombre.
    # Los apellidos largos invaden la columna de la edad y pdfplumber inserta un
    # espacio en ese borde; ese espacio (el pegado a la izquierda de la edad) es
    # espurio y partiría el apellido, así que se descarta. Los espacios reales
    # entre nombres quedan bien a la izquierda de la edad y se conservan.
    digit_xs = [x for t, x in zone if t.isdigit()]
    age_left = min(digit_xs) if digit_xs else float("inf")
    name_c = [t for t, x in zone
              if not t.isdigit() and not (t == " " and x >= age_left - 6)]
    lane = "".join(lane_c).strip()
    name = re.sub(r"\s+", " ", "".join(name_c)).strip()
    age = "".join(t for t, _ in zone if t.isdigit()).strip()
    team = "".join(team_c).strip()
    seed = "".join(seed_c).strip()
    if (re.fullmatch(r"\d{1,2}", lane) and re.fullmatch(r"\d{1,2}", age)
            and name and re.match(r"NT|[\d:]*\d\.\d{2}", seed)):
        return f"{lane} {name} {age} {team} {seed}"
    return raw


def _hytek_lines(pdf) -> list[str]:
    """Aplana el PDF HY-TEK a líneas limpias (título, jornada y inscripciones)."""
    out: list[str] = []
    title_done = False
    last_jornada = None
    for page in pdf.pages:
        for line in (page.extract_text() or "").splitlines():
            line = line.strip()
            if not title_done and _HY_TITLE.match(line):
                out.append(line)
                title_done = True
            elif _HY_JORNADA.search(line) and line != last_jornada:
                out.append(line)
                last_jornada = line
        mid = _split_x(page)
        crops = ([page.crop((0, 0, mid, page.height)),
                  page.crop((mid, 0, page.width, page.height))]
                 if mid else [page])
        for crop in crops:
            lines: dict[float, list] = {}
            for c in sorted(crop.chars, key=lambda c: (c["top"], c["x0"])):
                key = next((k for k in lines if abs(k - c["top"]) <= 2), None)
                lines.setdefault(c["top"] if key is None else key, []).append(c)
            ordered = [lines[top] for top in sorted(lines)]
            bounds = next((b for b in map(_column_bounds, ordered) if b), None)
            for line_chars in ordered:
                out.append(_rebuild_line(line_chars, bounds))
    return out


def _chars_to_line(chars: list, gap: float = 1.5) -> str:
    """Reconstruye una línea desde caracteres, agregando espacios por distancia x."""
    chars = sorted(chars, key=lambda c: c["x0"])
    out, prev = [], None
    for c in chars:
        if prev is not None and c["x0"] - prev["x1"] > gap:
            out.append(" ")
        out.append(c["text"])
        prev = c
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _positional_lines(page, bands: int = 3) -> list[str]:
    """Líneas de una página por bandas verticales.

    Algunos PDFs de Colombia Acuática imprimen dos o tres bloques horizontales.
    `extract_text()` mezcla bloques que comparten la misma altura y convierte
    media columna en parte del nombre. Leer por bandas preserva el flujo."""
    out: list[str] = []
    width = page.width / bands
    for i in range(bands):
        x0, x1 = i * width, (i + 1) * width
        chars = [c for c in page.chars if x0 <= c["x0"] < x1]
        grouped: dict[float, list] = {}
        for c in sorted(chars, key=lambda c: (c["top"], c["x0"])):
            key = next((k for k in grouped if abs(k - c["top"]) <= 2), None)
            grouped.setdefault(c["top"] if key is None else key, []).append(c)
        for top in sorted(grouped):
            line = _chars_to_line(grouped[top])
            if line:
                out.append(line)
    return out


def _colombia_lines(pdf) -> list[str]:
    """Aplana PDFs Colombia Acuática, separando columnas/bloques por posición."""
    out: list[str] = []
    for page in pdf.pages:
        text_lines = [(page.extract_text() or "").splitlines()]
        for line in text_lines[0]:
            if "liga" in line.lower() or _CO_SESSION.search(line):
                out.append(line.strip())
        out.extend(_positional_lines(page, bands=3))
    return out


# Campos del PDF que definen "la misma programación". Se excluyen los derivados
# de la base (event_id, swimmer_id), que dependen del estado de la base y no del
# contenido del programa.
_FINGERPRINT_FIELDS = (
    "event_number", "event_label", "gender", "category", "session_no",
    "session_date", "heat", "lane", "start_time", "swimmer_name", "club_code",
    "age", "seed_ms",
)


def fingerprint(competition: dict, entries: list[dict]) -> str:
    """Huella estable del contenido del programa, para detectar si cambió.

    Independiente del orden de las inscripciones y del estado de la base."""
    rows = sorted(
        "|".join(str(e.get(f, "")) for f in _FINGERPRINT_FIELDS) for e in entries
    )
    payload = (competition.get("pool_type") or "") + "\n" + "\n".join(rows)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def map_event_ids(entries: list[dict], event_index: list[tuple]) -> None:
    """Asigna event_id a cada entrada cruzando distancia+estilo con el catálogo.

    event_index: lista de (event_id, distance, stroke_key) construida desde la
    base. Modifica las entradas en sitio."""
    lookup = {(d, s): eid for eid, d, s in event_index}
    for e in entries:
        e["event_id"] = lookup.get((e["distance"], e["stroke"]))


def match_swimmers(entries: list[dict], swimmers: list[tuple]) -> dict:
    """Cruza por nombre normalizado las entradas con los nadadores de la base.

    swimmers: lista de (swimmer_id, swimmer_name). Asigna swimmer_id a cada
    entrada cuyo nombre coincide de forma única. Devuelve estadísticas."""
    index: dict[str, list[str]] = {}
    for sid, name in swimmers:
        index.setdefault(normalize_name(name), []).append(sid)
    matched = ambiguous = 0
    for e in entries:
        ids = index.get(normalize_name(e["swimmer_name"]))
        if ids and len(ids) == 1:
            e["swimmer_id"] = ids[0]
            matched += 1
        elif ids:
            ambiguous += 1
    return {"matched": matched, "ambiguous": ambiguous, "total": len(entries)}
