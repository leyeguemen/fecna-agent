"""Interpreta preguntas en lenguaje natural: intención, nadadores, piscina, género.

La prueba (evento) se resuelve aparte con el índice semántico.
"""

import re
import unicodedata
from dataclasses import dataclass, field

ID_RE = re.compile(r"\b\d{6,12}\b")
CATEGORY_RE = re.compile(r"\b(\d{1,2})\s*anos\b")

INTENT_PATTERNS = [
    ("compare", re.compile(r"\bcompara|\bversus\b|\bvs\b|\bcontra\b")),
    ("ranking", re.compile(r"\branking\b|\btop\b|mejores nadadores"
                           r"|mas rapid\w*|quien(es)? gano")),
    ("history", re.compile(r"evolucion|historial|progres|como va|ha mejorado")),
    ("best", re.compile(r"mejor (marca|tiempo|registro)|\brecord\b|marca personal")),
]

POOL_PATTERNS = [
    ("LC", re.compile(r"piscina larga|olimpica|\blc\b|piscina de 50")),
    ("SC", re.compile(r"piscina corta|\bsc\b|piscina de 25")),
]

GENDER_PATTERNS = [
    ("M", re.compile(r"masculino|hombres|varones|ninos")),
    ("F", re.compile(r"femenino|mujeres|damas|ninas")),
]


@dataclass
class ParsedQuestion:
    raw: str
    intent: str = "best"
    swimmer_ids: list[str] = field(default_factory=list)
    event_query: str | None = None
    pool_type: str | None = None
    gender: str | None = None
    category: str | None = None
    name_query: str | None = None   # fragmento que parece nombre de nadador
    explicit_intent: bool = False   # False = la intención se asumió por defecto


DISTANCE_WORDS = {
    "veinticinco": "25",
    "cincuenta": "50",
    "cien": "100",
    "doscientos": "200",
    "cuatrocientos": "400",
    "ochocientos": "800",
    "mil quinientos": "1500",
    "milquinientos": "1500",
}

STROKE_WORDS = (
    "libre", "free", "crol", "crawl",
    "espalda", "back", "dorso",
    "pecho", "breast", "braza",
    "mariposa", "fly", "butterfly",
    "combinado", "medley",
)

STROKE_RE = "|".join(re.escape(word) for word in sorted(STROKE_WORDS, key=len, reverse=True))
DISTANCE_WORD_RE = "|".join(re.escape(word) for word in sorted(DISTANCE_WORDS, key=len, reverse=True))


_EVENT_NUM_RE = re.compile(rf"\b(\d{{2,4}})\s*m?\s+({STROKE_RE})\b")
_EVENT_WORD_RE = re.compile(rf"\b({DISTANCE_WORD_RE})\s+({STROKE_RE})\b")

# Palabras de la pregunta que NO son parte del nombre de un nadador: pronombres,
# verbos de la consulta, entidades ya extraídas aparte (prueba/piscina/género) y
# saludos. Se usan (ya normalizadas) para aislar el fragmento que sí es nombre.
STOPWORDS = frozenset("""
    cual cuales es son el la los las un una unos unas de del al a en con y o u
    que quien quienes como por para desde hasta entre sobre me te se su sus mi
    mis lo le les este esta ese esa mismo misma
    muestrame muestra dame dime quiero necesito ver favor ayuda puedes puedo
    hacer haz
    mejor mejores marca marcas tiempo tiempos registro registros record records
    personal compara comparalo comparala comparame versus vs contra ranking top
    nadador nadadora nadadores piscina larga corta olimpica masculino femenino
    hombres mujeres damas varones ninos ninas anos categoria evolucion historial
    historia progreso progresion rapido rapida mas va gano ganaron ha mejorado
    hola buenas buenos dias tardes noches
""".split())


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def extract_event_query(text: str) -> str | None:
    """Extrae el fragmento de prueba: "800m libre", "cien espalda", etc."""
    match = _EVENT_NUM_RE.search(text)
    if match:
        return f"{match.group(1)} {match.group(2)}"

    match = _EVENT_WORD_RE.search(text)
    if match:
        return f"{DISTANCE_WORDS[match.group(1)]} {match.group(2)}"

    return None


def extract_name_query(text: str) -> str | None:
    """Aísla el fragmento de la pregunta que parece un nombre de nadador.

    Quita lo ya reconocido (ids, prueba, piscina, género, categoría) y las
    palabras de consulta (STOPWORDS); lo que queda son los tokens del nombre.
    Devuelve None si no queda nada. El texto puede venir sin normalizar."""
    work = normalize(text)
    work = ID_RE.sub(" ", work)
    work = _EVENT_NUM_RE.sub(" ", work)
    work = _EVENT_WORD_RE.sub(" ", work)
    for _, pattern in POOL_PATTERNS + GENDER_PATTERNS:
        work = pattern.sub(" ", work)
    work = CATEGORY_RE.sub(" ", work)
    tokens = [t for t in re.findall(r"[a-z0-9]+", work)
              if t not in STOPWORDS and not t.isdigit()]
    return " ".join(tokens) or None


def parse_question(question: str) -> ParsedQuestion:
    text = normalize(question)
    parsed = ParsedQuestion(raw=question)

    parsed.swimmer_ids = ID_RE.findall(text)
    parsed.event_query = extract_event_query(text)

    for intent, pattern in INTENT_PATTERNS:
        if pattern.search(text):
            parsed.intent = intent
            parsed.explicit_intent = True
            break
    else:
        if len(parsed.swimmer_ids) >= 2:
            parsed.intent = "compare"
            parsed.explicit_intent = True

    parsed.name_query = extract_name_query(text)

    for pool, pattern in POOL_PATTERNS:
        if pattern.search(text):
            parsed.pool_type = pool
            break

    for gender, pattern in GENDER_PATTERNS:
        if pattern.search(text):
            parsed.gender = gender
            break

    category = CATEGORY_RE.search(text)
    if category:
        parsed.category = f"{category.group(1)} AÑOS"

    return parsed
