"""Aísla la suite: ninguna prueba puede tocar una base Postgres real por accidente."""

import pytest


@pytest.fixture(autouse=True)
def _sin_base_remota(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
