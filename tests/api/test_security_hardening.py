"""Endurecimiento de la API: IP real para los límites de intentos, sesiones al cambiar la contraseña
y documentación interactiva apagada en producción."""

import os

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from fecna_agent import db


def _request(headers: dict, client=("10.0.0.7", 1234)) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "client": client})


def test_limite_de_intentos_usa_la_ip_que_entrega_cloudflare():
    from api.routers.auth import client_ip

    # Detrás de Render todos llegan desde la IP del proxy: sin el encabezado de Cloudflare se
    # compartiría un solo límite entre todos los usuarios.
    assert client_ip(_request({"CF-Connecting-IP": "181.50.1.2"})) == "181.50.1.2"
    assert client_ip(_request({"CF-Connecting-IP": "2800:e2:1::5"})) == "2800:e2:1::5"
    # X-Forwarded-For lo puede escribir el propio cliente (Render solo agrega): no se usa.
    assert client_ip(_request({"X-Forwarded-For": "1.2.3.4"})) == "10.0.0.7"
    # Un valor que no es una IP no sirve de llave (evita llaves arbitrarias).
    assert client_ip(_request({"CF-Connecting-IP": "no-es-ip"})) == "10.0.0.7"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("FECNA_DB", str(tmp_path / "read.db"))
    db.connect(tmp_path / "read.db").close()
    from api import main

    return TestClient(main.app)


def test_cambiar_contrasena_cierra_las_otras_sesiones_y_entrega_un_token_nuevo(client):
    import time

    from api import security

    reg = client.post("/auth/register", json={"email": "u@test.co", "password": "clave1234"}).json()
    otra = client.post("/auth/login", json={"email": "u@test.co", "password": "clave1234"}).json()
    old = {"Authorization": f"Bearer {reg['token']}"}
    assert client.get("/me", headers=old).status_code == 200
    time.sleep(1.1)  # el cambio ocurre después de emitir los tokens viejos (iat va en segundos)
    r = client.post("/me/password", json={"current": "clave1234", "new": "nueva1234"}, headers=old)
    assert r.status_code == 200 and r.json()["token"]
    security.clear_role_cache()
    # Las sesiones abiertas antes del cambio dejan de valer (la robada incluida)...
    assert client.get("/me", headers=old).status_code == 401
    assert client.get("/me", headers={"Authorization": f"Bearer {otra['token']}"}).status_code == 401
    # ...y quien cambió la contraseña sigue dentro con el token nuevo.
    assert client.get("/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).status_code == 200
    nuevo = client.post("/auth/login", json={"email": "u@test.co", "password": "nueva1234"}).json()
    assert client.get("/me", headers={"Authorization": f"Bearer {nuevo['token']}"}).status_code == 200


def test_documentacion_interactiva_apagada_en_render(monkeypatch):
    from api.main import docs_enabled

    monkeypatch.delenv("RENDER", raising=False)
    assert docs_enabled() is True
    monkeypatch.setenv("RENDER", "true")  # Render la define en todos sus servicios
    assert docs_enabled() is False
