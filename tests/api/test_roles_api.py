"""Roles y permisos: catálogo, gestión de usuarios y efecto inmediato de los cambios."""

import os

import pytest
from fastapi.testclient import TestClient

from fecna_agent import db, permisos


@pytest.fixture
def env(tmp_path, monkeypatch):
    read = tmp_path / "read.db"
    db.connect(read).close()
    monkeypatch.setenv("FECNA_DB", str(read))
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("FECNA_ADMIN_EMAIL", "boss@x.co")
    from api import main

    client = TestClient(main.app)

    def register(email):
        r = client.post("/auth/register", json={"email": email, "password": "Secreta123"})
        assert r.status_code == 201, r.text
        return r.json()

    def h(token):
        return {"Authorization": f"Bearer {token}"}

    return client, register, h


def test_catalogo_de_permisos():
    assert permisos.has("admin", "sincronizar") and permisos.has("admin", "gestionar_usuarios")
    assert permisos.has("user", "chat") and permisos.has("user", "ficha_redes")
    assert not permisos.has("user", "eliminar_programa") and not permisos.has("user", "gestionar_usuarios")
    assert permisos.permissions_for("rol-inventado") == [] and not permisos.has(None, "chat")
    assert set(permisos.permissions_for("admin")) == set(permisos.PERMISSIONS)


def test_login_y_me_devuelven_permisos(env):
    client, register, h = env
    user, admin = register("ana@x.co"), register("boss@x.co")
    assert "chat" in user["permissions"] and "sincronizar" not in user["permissions"]
    assert "sincronizar" in admin["permissions"]
    me = client.get("/auth/me", headers=h(user["token"])).json()
    assert me["role"] == "user" and me["permissions"] == permisos.permissions_for("user")


def test_solo_quien_gestiona_usuarios_los_ve(env):
    client, register, h = env
    user, admin = register("ana@x.co"), register("boss@x.co")
    assert client.get("/admin/users", headers=h(user["token"])).status_code == 403
    assert client.get("/admin/roles", headers=h(user["token"])).status_code == 403
    items = client.get("/admin/users", headers=h(admin["token"])).json()["items"]
    assert {u["email"] for u in items} == {"ana@x.co", "boss@x.co"}
    assert all("password_hash" not in u and "salt" not in u for u in items)
    assert client.get("/admin/users", params={"q": "ana"}, headers=h(admin["token"])).json()["items"][0]["email"] == "ana@x.co"
    roles = client.get("/admin/roles", headers=h(admin["token"])).json()
    assert {r["id"] for r in roles["roles"]} == {"user", "admin"}


def test_cambiar_rol_surte_efecto_de_inmediato(env):
    client, register, h = env
    user, admin = register("ana@x.co"), register("boss@x.co")
    uid = next(u["id"] for u in client.get("/admin/users", headers=h(admin["token"])).json()["items"] if u["email"] == "ana@x.co")
    # El token de Ana dice «user»: no puede sincronizar.
    assert client.get("/admin/sync/status", headers=h(user["token"])).status_code == 403
    r = client.put(f"/admin/users/{uid}/role", json={"role": "admin"}, headers=h(admin["token"]))
    assert r.status_code == 200
    # Sin volver a iniciar sesión: el servidor ya la reconoce como admin.
    assert client.get("/auth/me", headers=h(user["token"])).json()["role"] == "admin"
    assert client.get("/admin/sync/status", headers=h(user["token"])).status_code != 403
    # Y al quitárselo, lo pierde en el acto aunque su token siga diciendo «admin».
    r = client.put(f"/admin/users/{uid}/role", json={"role": "user"}, headers=h(admin["token"]))
    assert r.status_code == 200
    assert client.get("/admin/sync/status", headers=h(user["token"])).status_code == 403


def test_protecciones_al_cambiar_roles(env):
    client, register, h = env
    register("ana@x.co")
    admin = register("boss@x.co")
    users = client.get("/admin/users", headers=h(admin["token"])).json()["items"]
    boss_id = next(u["id"] for u in users if u["email"] == "boss@x.co")
    ana_id = next(u["id"] for u in users if u["email"] == "ana@x.co")
    assert client.put(f"/admin/users/{boss_id}/role", json={"role": "user"}, headers=h(admin["token"])).status_code == 409
    assert client.put(f"/admin/users/{ana_id}/role", json={"role": "superman"}, headers=h(admin["token"])).status_code == 422
    assert client.put("/admin/users/9999/role", json={"role": "user"}, headers=h(admin["token"])).status_code == 404


def test_no_se_puede_quitar_al_ultimo_admin(env):
    client, register, h = env
    ana = register("ana@x.co")
    boss = register("boss@x.co")
    users = client.get("/admin/users", headers=h(boss["token"])).json()["items"]
    ana_id = next(u["id"] for u in users if u["email"] == "ana@x.co")
    boss_id = next(u["id"] for u in users if u["email"] == "boss@x.co")
    client.put(f"/admin/users/{ana_id}/role", json={"role": "admin"}, headers=h(boss["token"]))
    # Ana (ya admin) intenta degradar a Boss: hay otro admin, así que se permite…
    assert client.put(f"/admin/users/{boss_id}/role", json={"role": "user"}, headers=h(ana["token"])).status_code == 200
    # …pero ahora Ana es la única y no puede degradarse a sí misma ni nadie quitarle el rol.
    assert client.put(f"/admin/users/{ana_id}/role", json={"role": "user"}, headers=h(ana["token"])).status_code == 409


def test_cuenta_borrada_pierde_acceso_de_admin(env):
    client, register, h = env
    admin = register("boss@x.co")
    assert client.get("/admin/sync/status", headers=h(admin["token"])).status_code != 403
    conn = db.connect(os.environ["FECNA_APP_DB"])
    conn.execute("DELETE FROM app_user WHERE email = 'boss@x.co'")
    conn.commit()
    conn.close()
    from api import security

    security.clear_role_cache()
    assert client.get("/admin/sync/status", headers=h(admin["token"])).status_code == 401
    assert client.get("/auth/me", headers=h(admin["token"])).status_code == 401
