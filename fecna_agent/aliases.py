"""Genera alias de pruebas para el índice semántico.

"50m Libre/50m Free" → "50 libre", "50 free", "cincuenta libre", "50 crol", ...
"""

import re

DISTANCE_WORDS = {
    "25": "veinticinco",
    "50": "cincuenta",
    "100": "cien",
    "200": "doscientos",
    "400": "cuatrocientos",
    "800": "ochocientos",
    "1500": "mil quinientos",
}

STROKE_ALIASES = {
    "libre": ["libre", "free", "crol", "crawl"],
    "espalda": ["espalda", "back", "dorso"],
    "pecho": ["pecho", "breast", "braza"],
    "mariposa": ["mariposa", "fly", "butterfly"],
    "combinado": ["combinado", "medley", "combinado individual"],
}


def event_aliases(event_name: str) -> list[str]:
    """Lista de alias para una prueba; siempre incluye el nombre oficial."""
    aliases = [event_name]
    lowered = event_name.lower()

    relay = re.search(r"(\d+)\s*x\s*(\d+)", lowered)
    distance = None if relay else _first(re.search(r"(\d+)\s*m", lowered))
    stroke_key = next(
        (key for key, names in STROKE_ALIASES.items()
         if any(name in lowered for name in names)),
        None,
    )
    if not stroke_key:
        return aliases

    prefixes = []
    if relay:
        prefixes.append(f"{relay.group(1)}x{relay.group(2)}")
        prefixes.append(f"relevo {relay.group(1)}x{relay.group(2)}")
    elif distance:
        prefixes.extend([distance, f"{distance}m"])
        if distance in DISTANCE_WORDS:
            prefixes.append(DISTANCE_WORDS[distance])

    for prefix in prefixes:
        for stroke in STROKE_ALIASES[stroke_key]:
            aliases.append(f"{prefix} {stroke}")
    return aliases


def _first(match: re.Match | None) -> str | None:
    return match.group(1) if match else None
