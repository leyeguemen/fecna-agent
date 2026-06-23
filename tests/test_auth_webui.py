"""Pruebas de helpers de auth en webui que no dependen del render de Streamlit."""

from fecna_agent import webui


def test_is_admin_sin_auth_es_true(monkeypatch):
    # Con el candado apagado, la app es de acceso total (modo local).
    monkeypatch.setattr(webui, "AUTH", False)
    assert webui.is_admin() is True


def test_is_admin_con_auth_sin_sesion_es_false(monkeypatch):
    monkeypatch.setattr(webui, "AUTH", True)
    monkeypatch.setattr(webui, "current_user", lambda: None)
    assert webui.is_admin() is False


def test_is_admin_con_auth_y_rol(monkeypatch):
    monkeypatch.setattr(webui, "AUTH", True)
    monkeypatch.setattr(webui, "current_user", lambda: {"role": "admin"})
    assert webui.is_admin() is True
    monkeypatch.setattr(webui, "current_user", lambda: {"role": "user"})
    assert webui.is_admin() is False


def test_needs_login(monkeypatch):
    # Sin candado: nunca pide login.
    monkeypatch.setattr(webui, "AUTH", False)
    monkeypatch.setattr(webui, "current_user", lambda: None)
    assert webui.needs_login() is False
    # Con candado y sin sesión: pide login.
    monkeypatch.setattr(webui, "AUTH", True)
    assert webui.needs_login() is True
    # Con candado y con sesión: no pide login.
    monkeypatch.setattr(webui, "current_user", lambda: {"role": "user"})
    assert webui.needs_login() is False
