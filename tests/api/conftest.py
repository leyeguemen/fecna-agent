"""Configuración compartida de las pruebas de la API.

Desactiva el rate limiting de slowapi para los tests (se fija ANTES de que
cualquier módulo de la API se importe, ya que el límite se construye una
sola vez al importar `api.routers.auth`)."""

import os

os.environ.setdefault("FECNA_RATELIMIT_OFF", "1")
