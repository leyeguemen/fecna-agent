"""Aísla la suite: ninguna prueba puede tocar una base Postgres real por accidente."""

import pytest


@pytest.fixture(autouse=True)
def _sin_base_remota(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)


@pytest.fixture(autouse=True)
def _sin_cache_de_roles():
    """La caché del rol vigente no debe filtrarse entre pruebas (los ids se repiten)."""
    from api import security

    security.clear_role_cache()
    yield
    security.clear_role_cache()
