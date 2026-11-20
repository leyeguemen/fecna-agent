"""Guarda para el SQL que escribe el LLM: un único SELECT sobre tablas públicas."""

import re

ALLOWED_TABLES = {"ranking_public", "catalogs", "competition", "competition_entry", "sync_log"}
MAX_ROWS = 200

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|do|"
    r"set|pragma|attach|vacuum|pg_\w+|information_schema|current_setting|lo_\w+)\b",
    re.IGNORECASE,
)
_SOURCES = re.compile(r"\b(?:from|join)\s+([A-Za-z_][\w.]*)", re.IGNORECASE)
_CTE_NAMES = re.compile(r"(?:\bwith\s+|,\s*)([A-Za-z_]\w*)\s+as\s*\(", re.IGNORECASE)


def check_select(sql: str) -> str:
    """Devuelve el SQL limpio o lanza ValueError con el motivo."""
    text = re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql, flags=re.S).strip().rstrip(";").strip()
    if not text:
        raise ValueError("Consulta vacía.")
    if ";" in text:
        raise ValueError("Solo se permite una sentencia.")
    if not re.match(r"(select|with)\b", text, re.IGNORECASE):
        raise ValueError("Solo se permite SELECT.")
    # Se ignoran literales de texto al buscar palabras prohibidas.
    bare = re.sub(r"'(?:[^']|'')*'", "''", text)
    if _FORBIDDEN.search(bare):
        raise ValueError("La consulta contiene palabras no permitidas.")
    bare = re.sub(r"\b(?:extract|substring|trim)\s*\([^)]*\)", " ", bare, flags=re.IGNORECASE)
    ctes = {m.lower() for m in _CTE_NAMES.findall(bare)}
    for source in _SOURCES.findall(bare):
        name = source.lower()
        if name not in ALLOWED_TABLES and name not in ctes:
            raise ValueError(f"Tabla no permitida: {source}. Usa: {', '.join(sorted(ALLOWED_TABLES))}.")
    return text
