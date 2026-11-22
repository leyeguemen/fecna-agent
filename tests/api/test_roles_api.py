"""Roles y permisos editables: CRUD, protecciones y efecto inmediato de los cambios."""

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


def _user_id(client, h, token, email):
    return next(u["id"] for u in client.get("/admin/users", headers=h(token)).json()["items"] if u["email"] == email)


def test_siembra_de_roles_y_permisos(tmp_path):
    conn = db.connect(tmp_path / "x.db")
    roles = {r["id"]: r for r in db.list_roles(conn)}
    assert set(roles) == {"user", "admin"}
    assert set(roles["admin"]["permissions"]) == set(permisos.SYSTEM_PERMISSIONS)
    # Quien se registra solo ve ranking, nadador y torneos: sin chat, comparar ni ficha para redes.
    assert set(roles["user"]["permissions"]) == {"ver_ranking", "ver_nadador", "ver_torneos"}
    # Volver a conectar no pisa lo que el admin haya cambiado.
    db.save_role(conn, "user", "Usuario", ["chat"], create=False)
    conn.close()
    again = {r["id"]: r for r in db.list_roles(db.connect(tmp_path / "x.db"))}
    assert again["user"]["permissions"] == ["chat"]


def test_login_y_me_devuelven_permisos(env):
    client, register, h = env
    user, admin = register("ana@x.co"), register("boss@x.co")
    assert set(user["permissions"]) == {"ver_ranking", "ver_nadador", "ver_torneos"}
    assert "sincronizar" in admin["permissions"]
    me = client.get("/auth/me", headers=h(user["token"])).json()
    assert me["role"] == "user" and "ver_ranking" in me["permissions"] and "chat" not in me["permissions"]


def test_solo_quien_gestiona_usuarios_ve_roles_y_usuarios(env):
    client, register, h = env
    user, admin = register("ana@x.co"), register("boss@x.co")
    for path in ("/admin/users", "/admin/roles"):
        assert client.get(path, headers=h(user["token"])).status_code == 403
    items = client.get("/admin/users", headers=h(admin["token"])).json()["items"]
    assert {u["email"] for u in items} == {"ana@x.co", "boss@x.co"}
    assert all("password_hash" not in u and "salt" not in u for u in items)
    data = client.get("/admin/roles", headers=h(admin["token"])).json()
    assert {r["id"] for r in data["roles"]} == {"user", "admin"}
    assert {p["key"] for p in data["permissions"]} == set(permisos.SYSTEM_PERMISSIONS)


def test_crud_de_roles(env):
    client, register, h = env
    register("ana@x.co")
    t = register("boss@x.co")["token"]
    H = h(t)
    r = client.post("/admin/roles", json={"id": "entrenador", "name": "Entrenador", "permissions": ["chat", "comparar"]}, headers=H)
    assert r.status_code == 201
    assert client.post("/admin/roles", json={"id": "entrenador", "name": "X"}, headers=H).status_code == 409
    assert client.post("/admin/roles", json={"id": "Mal Id!", "name": "X"}, headers=H).status_code == 422
    assert client.post("/admin/roles", json={"id": "otro", "name": "X", "permissions": ["no_existe"]}, headers=H).status_code == 422
    assert client.put("/admin/roles/entrenador", json={"name": "Entrenador club", "permissions": ["chat"]}, headers=H).status_code == 200
    role = next(x for x in client.get("/admin/roles", headers=H).json()["roles"] if x["id"] == "entrenador")
    assert role["name"] == "Entrenador club" and role["permissions"] == ["chat"] and role["users"] == 0
    # Con usuarios asignados no se puede borrar.
    uid = _user_id(client, h, t, "ana@x.co")
    assert client.put(f"/admin/users/{uid}/role", json={"role": "entrenador"}, headers=H).status_code == 200
    assert client.delete("/admin/roles/entrenador", headers=H).status_code == 409
    client.put(f"/admin/users/{uid}/role", json={"role": "user"}, headers=H)
    assert client.delete("/admin/roles/entrenador", headers=H).status_code == 204
    assert client.delete("/admin/roles/entrenador", headers=H).status_code == 404


def test_roles_de_sistema_protegidos(env):
    client, register, h = env
    H = h(register("boss@x.co")["token"])
    assert client.delete("/admin/roles/admin", headers=H).status_code == 409
    assert client.delete("/admin/roles/user", headers=H).status_code == 409
    assert client.put("/admin/roles/admin", json={"name": "Admin", "permissions": []}, headers=H).status_code == 409


def test_crud_de_permisos_y_admin_recibe_los_nuevos(env):
    client, register, h = env
    H = h(register("boss@x.co")["token"])
    assert client.post("/admin/permissions", json={"key": "ver_marcas_minimas", "label": "Ver marcas mínimas"}, headers=H).status_code == 201
    assert client.post("/admin/permissions", json={"key": "ver_marcas_minimas", "label": "X"}, headers=H).status_code == 409
    data = client.get("/admin/roles", headers=H).json()
    assert "ver_marcas_minimas" in next(r for r in data["roles"] if r["id"] == "admin")["permissions"]
    assert client.put("/admin/permissions/ver_marcas_minimas", json={"label": "Marcas mínimas"}, headers=H).status_code == 200
    # Los de sistema se renombran pero no se borran; los propios sí.
    assert client.delete("/admin/permissions/chat", headers=H).status_code == 409
    assert client.put("/admin/permissions/chat", json={"label": "Hablar con el chat"}, headers=H).status_code == 200
    assert client.delete("/admin/permissions/ver_marcas_minimas", headers=H).status_code == 204
    assert client.delete("/admin/permissions/ver_marcas_minimas", headers=H).status_code == 404


def test_usuario_nuevo_solo_ve_ranking_nadador_y_torneos(env):
    client, register, h = env
    A = h(register("ana@x.co")["token"])
    assert client.get("/catalogs", headers=A).status_code == 200  # ranking
    assert client.get("/swimmers/search", params={"q": "ana"}, headers=A).status_code == 200  # nadador
    assert client.get("/competitions", headers=A).status_code == 200  # torneos
    # Sin chat, sin comparar, sin ficha para redes.
    assert client.post("/ask", json={"question": "hola"}, headers=A).status_code == 403
    assert client.get("/swimmers/compare", params={"a": "1", "b": "2", "event_id": "x"}, headers=A).status_code == 403
    assert client.post("/swimmers/1/ficha-redes", headers=A).status_code == 403
    # Y sin sesión, ni los campeonatos (antes eran públicos).
    assert client.get("/competitions").status_code == 401


def test_cambiar_permisos_de_un_rol_surte_efecto_de_inmediato(env):
    client, register, h = env
    ana, boss = register("ana@x.co"), register("boss@x.co")
    H, A = h(boss["token"]), h(ana["token"])
    assert client.get("/competitions", headers=A).status_code == 200
    assert client.get("/swimmers/compare", params={"a": "1", "b": "2", "event_id": "x"}, headers=A).status_code == 403
    # El admin le da «comparar» al rol Usuario y le quita «ver_torneos»: Ana lo nota sin volver a entrar.
    client.put("/admin/roles/user", json={"name": "Usuario", "permissions": ["ver_ranking", "ver_nadador", "comparar"]}, headers=H)
    assert client.get("/swimmers/compare", params={"a": "1", "b": "2", "event_id": "x"}, headers=A).status_code != 403
    assert client.get("/competitions", headers=A).status_code == 403
    me = client.get("/auth/me", headers=A).json()
    assert "comparar" in me["permissions"] and "ver_torneos" not in me["permissions"]
    # Un rol propio con solo el chat: ya no ve ranking.
    client.post("/admin/roles", json={"id": "basico", "name": "Básico", "permissions": ["chat"]}, headers=H)
    uid = _user_id(client, h, boss["token"], "ana@x.co")
    client.put(f"/admin/users/{uid}/role", json={"role": "basico"}, headers=H)
    assert client.get("/catalogs", headers=A).status_code == 403


def test_cambiar_rol_surte_efecto_de_inmediato_y_protecciones(env):
    client, register, h = env
    ana, boss = register("ana@x.co"), register("boss@x.co")
    H, A = h(boss["token"]), h(ana["token"])
    uid, bid = _user_id(client, h, boss["token"], "ana@x.co"), _user_id(client, h, boss["token"], "boss@x.co")
    assert client.get("/admin/sync/status", headers=A).status_code == 403
    assert client.put(f"/admin/users/{uid}/role", json={"role": "admin"}, headers=H).status_code == 200
    assert client.get("/auth/me", headers=A).json()["role"] == "admin"  # sin volver a iniciar sesión
    assert client.get("/admin/sync/status", headers=A).status_code != 403
    # No se cambia el propio rol, ni se quita al último admin, ni se asigna un rol inexistente.
    assert client.put(f"/admin/users/{bid}/role", json={"role": "user"}, headers=H).status_code == 409
    assert client.put(f"/admin/users/{uid}/role", json={"role": "inventado"}, headers=H).status_code == 422
    assert client.put("/admin/users/9999/role", json={"role": "user"}, headers=H).status_code == 404
    # Boss degrada a Ana: pierde el acceso al instante aunque su token diga «admin».
    assert client.put(f"/admin/users/{uid}/role", json={"role": "user"}, headers=H).status_code == 200
    assert client.get("/admin/sync/status", headers=A).status_code == 403
    # Con dos admins, uno sí puede degradar al otro; al quedar uno solo, no.
    client.put(f"/admin/users/{uid}/role", json={"role": "admin"}, headers=H)
    assert client.put(f"/admin/users/{bid}/role", json={"role": "user"}, headers=A).status_code == 200
    assert client.put(f"/admin/users/{uid}/role", json={"role": "user"}, headers=A).status_code == 409


def test_cuenta_borrada_pierde_acceso(env):
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


def test_permiso_de_sistema_nuevo_se_siembra_en_una_base_existente(tmp_path):
    """Si una versión del código agrega un permiso de sistema, una base ya creada lo recibe (y el admin)."""
    conn = db.connect(tmp_path / "x.db")
    conn.execute("DELETE FROM app_permission WHERE key = 'ver_ranking'")
    conn.execute("DELETE FROM role_permission WHERE permission_key = 'ver_ranking'")
    conn.commit()
    db.seed_roles(conn)
    roles = {r["id"]: r for r in db.list_roles(conn)}
    assert "ver_ranking" in roles["admin"]["permissions"]
    assert "ver_ranking" in db.permission_keys(conn)
    assert "ver_ranking" not in roles["user"]["permissions"]  # no se le devuelve a un rol que se lo quitaron


def test_historial_por_demanda_exige_sincronizar_y_nadador_existente(env):
    client, register, h = env
    user, admin = register("ana@x.co"), register("boss@x.co")
    for method in (client.get, client.post):
        assert method("/admin/swimmers/1/historial", headers=h(user["token"])).status_code == 403
        assert method("/admin/swimmers/zzz/historial", headers=h(admin["token"])).status_code == 404
