"""Normalización de tiempos de natación.

Los tiempos llegan como texto "HH:MM:SS.cc" y se convierten a milisegundos
para que las comparaciones sean exactas (las centésimas importan).
"""

import re

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})\.(\d{1,3})$")


def time_to_ms(raw: str) -> int:
    """Convierte '00:00:28.84' → 28840."""
    match = _TIME_RE.match(raw.strip())
    if not match:
        raise ValueError(f"Formato de tiempo no reconocido: {raw!r}")
    hours, minutes, seconds, fraction = match.groups()
    fraction_ms = int(fraction.ljust(3, "0"))
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + fraction_ms


def ms_to_time(ms: int) -> str:
    """Convierte 28840 → '00:00:28.84' (centésimas)."""
    if ms < 0:
        raise ValueError("Los milisegundos no pueden ser negativos")
    hours, rest = divmod(ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, rest = divmod(rest, 1000)
    centiseconds = rest // 10
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def diff_seconds(ms_a: int, ms_b: int) -> float:
    """Diferencia absoluta en segundos entre dos marcas."""
    return abs(ms_a - ms_b) / 1000
