"""Recuperar contraseña: /auth/forgot y /auth/reset."""

import time

import pytest
from fastapi.testclient import TestClient

from api import correo, main
from fecna_agent import db


@pytest.fixture
def enviados(monkeypatch):
    sent = []
    monkeypatch.setenv("BREVO_API_KEY", "clave")
    monkeypatch.setenv("MAIL_FROM", "natia@x.co")
    monkeypatch.setattr(correo, "send_reset_code", lambda to, code, minutes: sent.append((to, code)))
    return sent


@pytest.fixture
def client(tmp_path, monkeypatch, enviados):
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app.db"))
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FECNA_ADMIN_EMAIL", raising=False)
    c = TestClient(main.app)
    c.post("/auth/register", json={"email": "ana@x.co", "password": "Vieja1234"})
    return c


def _codigo(client, enviados, email="ana@x.co"):
    assert client.post("/auth/forgot", json={"email": email}).status_code == 202
    return enviados[-1][1]


def test_responde_igual_exista_o_no_la_cuenta(client, enviados):
    a = client.post("/auth/forgot", json={"email": "ANA@x.co "})
    b = client.post("/auth/forgot", json={"email": "nadie@x.co"})
    assert a.status_code == b.status_code == 202
    assert a.json() == b.json()
    assert [to for to, _ in enviados] == ["ana@x.co"]
    assert len(enviados[0][1]) == 6 and enviados[0][1].isdigit()


def test_con_el_codigo_cambia_la_contrasena_y_cierra_las_otras_sesiones(client, enviados):
    vieja = client.post("/auth/login", json={"email": "ana@x.co", "password": "Vieja1234"}).json()["token"]
    code = _codigo(client, enviados)
    time.sleep(1.1)  # el cambio ocurre después de emitir el token viejo (iat va en segundos)
    r = client.post("/auth/reset", json={"email": "ana@x.co", "code": code, "password": "Nueva1234"})
    assert r.status_code == 200 and r.json()["token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {vieja}"}).status_code == 401
    assert client.post("/auth/login", json={"email": "ana@x.co", "password": "Vieja1234"}).status_code == 401
    assert client.post("/auth/login", json={"email": "ana@x.co", "password": "Nueva1234"}).status_code == 200
    # El código se usa una sola vez.
    otra = client.post("/auth/reset", json={"email": "ana@x.co", "code": code, "password": "Otra12345"})
    assert otra.status_code == 400


def test_cinco_intentos_fallidos_anulan_el_codigo(client, enviados):
    code = _codigo(client, enviados)
    malo = "000000" if code != "000000" else "111111"
    for _ in range(db.RESET_MAX_ATTEMPTS):
        r = client.post("/auth/reset", json={"email": "ana@x.co", "code": malo, "password": "Nueva1234"})
        assert r.status_code == 400
    r = client.post("/auth/reset", json={"email": "ana@x.co", "code": code, "password": "Nueva1234"})
    assert r.status_code == 400


def test_contrasena_invalida_no_gasta_intentos(client, enviados):
    code = _codigo(client, enviados)
    for _ in range(db.RESET_MAX_ATTEMPTS + 1):
        r = client.post("/auth/reset", json={"email": "ana@x.co", "code": code, "password": "corta"})
        assert r.status_code == 400 and "8 caracteres" in r.json()["detail"]
    r = client.post("/auth/reset", json={"email": "ana@x.co", "code": code, "password": "Nueva1234"})
    assert r.status_code == 200


def test_no_reenvia_antes_de_un_minuto(client, enviados):
    _codigo(client, enviados)
    client.post("/auth/forgot", json={"email": "ana@x.co"})
    assert len(enviados) == 1


def test_codigo_vencido(tmp_path):
    conn = db.connect(tmp_path / "a.db")
    db.create_user(conn, "b@x.co", "Vieja1234")
    _, code = db.start_password_reset(conn, "b@x.co", now=1000)
    with pytest.raises(ValueError, match="venció"):
        db.finish_password_reset(conn, "b@x.co", code, "Nueva1234", now=1000 + db.RESET_TTL + 1)


def test_cuenta_desactivada_no_recibe_codigo(tmp_path):
    conn = db.connect(tmp_path / "a.db")
    user = db.create_user(conn, "b@x.co", "Vieja1234")
    conn.execute("UPDATE app_user SET active = 0 WHERE id = ?", (user["id"],))
    conn.commit()
    assert db.start_password_reset(conn, "b@x.co", now=1000) is None


def test_sin_correo_configurado_responde_503(client, monkeypatch):
    monkeypatch.delenv("BREVO_API_KEY")
    assert client.post("/auth/forgot", json={"email": "ana@x.co"}).status_code == 503
