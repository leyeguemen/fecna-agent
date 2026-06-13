"""Catálogos de pruebas, categorías, piscinas y ligas.

Se extraen de los <select> del formulario de reportes; con esto se mapean
todos los IDs de pruebas (pendiente del descubrimiento técnico).
"""

import re
from html.parser import HTMLParser

from .extractor import INDEX_URL, TIMEOUT, _check, build_session

# Las categorías no vienen en un <select>: están hardcodeadas en el JS de la
# página (función cambia()): opt_1 = másters, opt_2 = femenino, opt_3 = masculino.
CATEGORY_ARRAYS = {
    "opt_1": "categoria_master",
    "opt_2": "categoria_F",
    "opt_3": "categoria_M",
}
_ARRAY_RE = re.compile(r"var\s+(opt_\d)\s*=\s*new Array\((.*?)\)\s*;", re.DOTALL)

# Selects del formulario que interesan (nombre HTML → kind local)
SELECT_KINDS = {
    "prueba": "prueba",
    "categoria[]": "categoria",
    "piscina": "piscina",
    "liga": "liga",
    "torneo": "torneo",
    "genero": "genero",
}


class _SelectParser(HTMLParser):
    """Extrae las opciones (value, label) de cada <select name=...>."""

    def __init__(self):
        super().__init__()
        self.selects: dict[str, list[tuple[str, str]]] = {}
        self._select: str | None = None
        self._option_value: str | None = None
        self._option_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select":
            self._select = attrs.get("name")
            if self._select is not None:
                self.selects.setdefault(self._select, [])
        elif tag == "option" and self._select is not None:
            self._option_value = attrs.get("value", "")
            self._option_text = []

    def handle_data(self, data):
        if self._option_value is not None:
            self._option_text.append(data)

    def handle_endtag(self, tag):
        if tag == "option" and self._select is not None and self._option_value is not None:
            label = "".join(self._option_text).strip()
            if self._option_value or label:
                self.selects[self._select].append((self._option_value, label))
            self._option_value = None
        elif tag == "select":
            self._select = None


def parse_catalogs(html: str) -> dict[str, list[tuple[str, str]]]:
    """Devuelve {kind: [(code, label), ...]} para los selects de interés
    más las categorías embebidas en el JS de la página."""
    parser = _SelectParser()
    parser.feed(html)
    catalogs = {
        kind: parser.selects[name]
        for name, kind in SELECT_KINDS.items()
        if parser.selects.get(name)
    }
    catalogs.update(parse_category_arrays(html))
    return catalogs


def parse_category_arrays(html: str) -> dict[str, list[tuple[str, str]]]:
    catalogs = {}
    for match in _ARRAY_RE.finditer(html):
        kind = CATEGORY_ARRAYS.get(match.group(1))
        if not kind:
            continue
        values = re.findall(r'"([^"]+)"', match.group(2))
        catalogs[kind] = [(value, value) for value in values]
    return catalogs


def fetch_catalogs(session=None) -> dict[str, list[tuple[str, str]]]:
    session = session or build_session()
    response = session.get(INDEX_URL, timeout=TIMEOUT)
    _check(response)
    return parse_catalogs(response.text)
