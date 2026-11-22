"""Reportes desde la app: permiso, saneamiento y envío al workflow (sin llamar a GitHub de verdad)."""

import pytest
from fastapi.testclient import TestClient

from fecna_agent import db


@pytest.fixture
def env(tmp_path, monkeypatch):
    read = tmp_path / "read.db"
    db.connect(read).close()
    monkeypatch.setenv("FECNA_DB", str(read))
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("FECNA_ADMIN_EMAIL", "boss@x.co")
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPO", "o/r")
    from api import main
    from api.routers import reports

    reports._sent.clear()
    calls = []

    class Resp:
        status_code = 204

    monkeypatch.setattr(reports.requests, "post", lambda url, **kw: (calls.append((url, kw)) or Resp()))
    client = TestClient(main.app)

    def register(email):
        r = client.post("/auth/register", json={"email": email, "password": "Secreta123"})
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}

    return client, register, calls


BODY = {"title": "No abre el chat", "description": "Al abrir Torneos se queda cargando", "screen": "Torneos", "platform": "android", "app_version": "1.0.0"}


def test_usuario_nuevo_no_puede_reportar_hasta_que_se_habilite(env):
    client, register, calls = env
    user, boss = register("ana@x.co"), register("boss@x.co")
    assert client.post("/reports", json=BODY, headers=user).status_code == 403
    assert calls == []
    # El admin habilita el permiso en el rol Usuario desde Seguridad.
    role = next(r for r in client.get("/admin/roles", headers=boss).json()["roles"] if r["id"] == "user")
    client.put("/admin/roles/user", json={"name": "Usuario", "permissions": role["permissions"] + ["reportar_problema"]}, headers=boss)
    assert client.post("/reports", json=BODY, headers=user).status_code == 202
    assert len(calls) == 1


def test_el_admin_puede_reportar_y_va_al_workflow_sin_datos_personales(env):
    client, register, calls = env
    boss = register("boss@x.co")
    r = client.post("/reports", json={**BODY, "description": "Hola @alguien mira esto\x00"}, headers=boss)
    assert r.status_code == 202
    url, kw = calls[0]
    assert url.endswith("/repos/o/r/actions/workflows/reporte.yml/dispatches")
    inputs = kw["json"]["inputs"]
    assert inputs["titulo"] == "[App] No abre el chat"
    assert "@alguien" not in inputs["cuerpo"] and "\x00" not in inputs["cuerpo"]  # sin menciones activas
    assert "boss@x.co" not in inputs["cuerpo"]  # nunca el correo
    assert "pantalla: Torneos" in inputs["cuerpo"] and "android" in inputs["etiquetas"]


def test_valida_datos_y_limita_la_cantidad(env, monkeypatch):
    client, register, calls = env
    boss = register("boss@x.co")
    assert client.post("/reports", json={**BODY, "title": "ab"}, headers=boss).status_code == 422
    assert client.post("/reports", json={**BODY, "description": "x" * 3000}, headers=boss).status_code == 422
    assert client.post("/reports", json=BODY).status_code == 401
    from api.routers import reports

    monkeypatch.setattr(reports, "_DAILY_LIMIT", 1)
    reports._sent.clear()
    assert client.post("/reports", json=BODY, headers=boss).status_code == 202
    assert client.post("/reports", json=BODY, headers=boss).status_code == 429
