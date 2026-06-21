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
_GENDER = {"Women": "F", "Men": "M", "Mixed": "X"}


def _parse_hytek(lines: list[str]) -> tuple[dict, list[dict]]:
    competition = {"name": None, "pool_type": None, "source_format": "hytek"}
    entries: list[dict] = []
    ev: dict | None = None
    heat = start_time = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if competition["name"] is None and _HY_TITLE.match(line):
            competition["name"] = line
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
                entries.append(_entry(ev, heat, start_time, lane, name, team, age, seed))
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


def _entry(ev, heat, start_time, lane, name, club, age, seed) -> dict:
    return {
        "event_number": ev["event_number"], "event_label": ev["event_label"],
        "event_id": None, "distance": ev["distance"], "stroke": ev["stroke"],
        "gender": ev["gender"], "category": ev["category"],
        "session_no": None, "session_date": None,
        "heat": heat, "lane": int(lane), "start_time": start_time,
        "swimmer_name": re.sub(r"\s+", " ", name).strip(), "club_code": club.strip(),
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
    """Lee un PDF (ruta o bytes/buffer) y lo parsea. Requiere pdfplumber."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return parse_text("\n".join(text_parts))


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
