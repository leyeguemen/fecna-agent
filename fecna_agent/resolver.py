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
    ("ranking", re.compile(r"\branking\b|\btop\b|mejores nadadores")),
    ("history", re.compile(r"evolucion|historial|progres")),
    ("best", re.compile(r"mejor (marca|tiempo|registro)")),
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


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def extract_event_query(text: str) -> str | None:
    """Extrae el fragmento de prueba: "800m libre", "cien espalda", etc."""
    match = re.search(rf"\b(\d{{2,4}})\s*m?\s+({STROKE_RE})\b", text)
    if match:
        return f"{match.group(1)} {match.group(2)}"

    match = re.search(rf"\b({DISTANCE_WORD_RE})\s+({STROKE_RE})\b", text)
    if match:
        return f"{DISTANCE_WORDS[match.group(1)]} {match.group(2)}"

    return None


def parse_question(question: str) -> ParsedQuestion:
    text = normalize(question)
    parsed = ParsedQuestion(raw=question)

    parsed.swimmer_ids = ID_RE.findall(text)
    parsed.event_query = extract_event_query(text)

    for intent, pattern in INTENT_PATTERNS:
        if pattern.search(text):
            parsed.intent = intent
            break
    else:
        if len(parsed.swimmer_ids) >= 2:
            parsed.intent = "compare"

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
