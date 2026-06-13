"""Categorías deportivas → rango de edad competitiva.

La fuente no incluye la categoría en cada resultado, pero sí la fecha de
nacimiento. La categoría se determina por año de nacimiento: edad = año de
referencia de la consulta − año de nacimiento (no la edad al momento de cada
resultado). "12 AÑOS" → 12, "10 Y 11 Infantil A" → 10-11, "21 Y MAS" → 21+.
"""

import re

_MAS_RE = re.compile(r"m[aá]s", re.IGNORECASE)


def age_range(label: str) -> tuple[int, int] | None:
    """Rango (min, max) de edad para una etiqueta de categoría, o None."""
    numbers = [int(n) for n in re.findall(r"\d+", label)]
    if not numbers:
        return None
    if _MAS_RE.search(label):
        return (numbers[0], 999)
    if len(numbers) >= 2:
        return (min(numbers), max(numbers))
    return (numbers[0], numbers[0])
