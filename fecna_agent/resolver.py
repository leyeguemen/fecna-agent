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
    pool_type: str | None = None
    gender: str | None = None
    category: str | None = None


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def parse_question(question: str) -> ParsedQuestion:
    text = normalize(question)
    parsed = ParsedQuestion(raw=question)

    parsed.swimmer_ids = ID_RE.findall(text)

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
