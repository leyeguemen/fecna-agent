"""Aísla la suite: ninguna prueba puede tocar una base Postgres real por accidente."""

import pytest


@pytest.fixture(autouse=True)
def _sin_base_remota(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Ninguna prueba debe tocar la base local de la app (data/fecna_app.db): cada una usa la suya.
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app_por_defecto.db"))


@pytest.fixture(autouse=True)
def _sin_cache_de_roles():
    """La caché del rol vigente no debe filtrarse entre pruebas (los ids se repiten)."""
    from api import security

    security.clear_role_cache()
    yield
    security.clear_role_cache()


@pytest.fixture(autouse=True)
def _usuario_con_todo_salvo_en_pruebas_de_roles(request, monkeypatch):
    """El rol de partida de «user» es mínimo (ranking, nadador, torneos). Las pruebas que no tratan
    de permisos usan un usuario con todo lo de consumo; test_roles_api prueba los valores reales."""
    if "test_roles_api" in request.node.nodeid:
        return
    from fecna_agent import permisos

    full = {"ver_ranking", "ver_nadador", "ver_torneos", "chat", "comparar", "ficha_redes"}
    monkeypatch.setitem(permisos.DEFAULT_ROLES, "user", ("Usuario", full))
