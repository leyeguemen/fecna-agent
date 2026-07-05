import jwt
import pytest
from fastapi.testclient import TestClient

from api import main, security


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app.db"))
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("FECNA_ADMIN_EMAIL", raising=False)
    return TestClient(main.app)


def test_register_ok(client):
    resp = client.post("/auth/register", json={"email": "a@b.co", "password": "Secreta123"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@b.co"
    assert body["role"] == "user"
    payload = jwt.decode(body["token"], security._secret(), algorithms=["HS256"])
    assert payload["email"] == "a@b.co"
    assert payload["role"] == "user"


def test_register_admin_role_por_env(client, monkeypatch):
    monkeypatch.setenv("FECNA_ADMIN_EMAIL", "jefe@x.co")
    resp = client.post("/auth/register", json={"email": "jefe@x.co", "password": "Secreta123"})
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"


def test_register_duplicado(client):
    client.post("/auth/register", json={"email": "a@b.co", "password": "Secreta123"})
    resp = client.post("/auth/register", json={"email": "a@b.co", "password": "Secreta123"})
    assert resp.status_code == 400
    assert "ya está registrado" in resp.json()["detail"]


def test_register_password_invalida(client):
    resp = client.post("/auth/register", json={"email": "a@b.co", "password": "corta1"})
    assert resp.status_code == 400


def test_login_ok_y_credenciales_invalidas(client):
    client.post("/auth/register", json={"email": "a@b.co", "password": "Secreta123"})

    ok = client.post("/auth/login", json={"email": "a@b.co", "password": "Secreta123"})
    assert ok.status_code == 200
    assert ok.json()["token"]
    assert ok.json()["role"] == "user"

    mal = client.post("/auth/login", json={"email": "a@b.co", "password": "otraClave1"})
    assert mal.status_code == 401
    assert mal.json()["detail"] == "Email o contraseña incorrectos."


def test_me_sin_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "No autenticado."


def test_me_con_token(client):
    reg = client.post("/auth/register", json={"email": "a@b.co", "password": "Secreta123"})
    token = reg.json()["token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "a@b.co"
    assert body["role"] == "user"


def test_me_token_manipulado(client):
    reg = client.post("/auth/register", json={"email": "a@b.co", "password": "Secreta123"})
    token = reg.json()["token"]
    ultimo = token[-1]
    manipulado = token[:-1] + ("a" if ultimo != "a" else "b")
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {manipulado}"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "No autenticado."
