"""Cliente HTTP para el reporte Ranking de FECNA/Ecoapplet.

Flujo confirmado:
  1. GET  /fecna/reportes/index       → crea sesión PHP (PHPSESSID)
  2. POST /fecna/reportes/index       → guarda los filtros en la sesión
  3. GET  /fecna/reportes/getRanking  → devuelve JSON con los filtros activos
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://ecoapplet.co"
INDEX_URL = f"{BASE_URL}/fecna/reportes/index"
RANKING_URL = f"{BASE_URL}/fecna/reportes/getRanking"

TIMEOUT = 30

# Campos mínimos que debe traer cada registro; si faltan, la estructura
# del sitio cambió y hay que revisar el extractor.
REQUIRED_FIELDS = {"identificacion", "tiempo", "prueba_id", "piscina"}


class SiteBlockedError(RuntimeError):
    """El sitio activó protección anti-bot o bloqueó esta IP.

    Se manifiesta como 415 en todas las rutas (openresty) o como una página
    de verificación. Reintentar de inmediato solo empeora el bloqueo."""


def _check(response) -> None:
    if response.status_code == 415 or "being verified" in response.text[:2000]:
        raise SiteBlockedError(
            "ecoapplet.co está rechazando las peticiones (verificación anti-bot "
            "o bloqueo temporal de IP). Espera unas horas antes de reintentar y "
            "usa rangos de fecha cortos en 'sync' para reducir la carga."
        )
    response.raise_for_status()


def fetch_ranking(
    inicio: str,
    fin: str,
    genero: str = "",
    categoria: str | list[str] = "",
    prueba: str = "",
    piscina: str = "",
    torneo: str = "",
    liga: str = "",
    master: str = "0",
    session: requests.Session | None = None,
) -> list[dict]:
    """Extrae el ranking con los filtros dados. Devuelve la lista JSON cruda."""
    session = session or build_session()

    _check(session.get(INDEX_URL, timeout=TIMEOUT))

    # categoria[] es un select múltiple: se pueden pedir varias en una petición
    categorias = [categoria] if isinstance(categoria, str) else list(categoria)
    payload = [
        ("inicio", inicio),
        ("fin", fin),
        ("torneo", torneo),
        ("genero", genero),
        ("master", master),
        *(("categoria[]", c) for c in categorias),
        ("liga", liga),
        ("prueba", prueba),
        ("piscina", piscina),
    ]
    _check(session.post(INDEX_URL, data=payload, timeout=TIMEOUT))

    response = session.get(
        RANKING_URL,
        params={"_": int(time.time() * 1000)},
        timeout=TIMEOUT,
    )
    _check(response)

    rows = response.json()
    if not isinstance(rows, list):
        raise ValueError(f"Respuesta inesperada de getRanking: {type(rows).__name__}")
    validate_structure(rows)
    return rows


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": INDEX_URL,
        "Origin": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    })
    return session


def validate_structure(rows: list[dict]) -> None:
    """Verifica que los registros tengan los campos esperados (riesgo: el
    sitio puede cambiar la estructura sin aviso)."""
    if not rows:
        return
    missing = REQUIRED_FIELDS - rows[0].keys()
    if missing:
        raise ValueError(f"Campos faltantes en la respuesta: {sorted(missing)}")
