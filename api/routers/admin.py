"""Endpoints de administración: disparar y consultar la sincronización del ranking.

La sincronización corre en GitHub Actions (workflow_dispatch) y escribe en
Postgres. Variables: GITHUB_TOKEN (fine-grained, permiso Actions: read/write),
GITHUB_REPO ("usuario/repo"), GITHUB_WORKFLOW (defecto sync.yml), GITHUB_REF (defecto main).
"""

import os
from typing import Literal

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from api import security
from api.deps import app_conn, read_conn
from fecna_agent import db, historial, permisos

router = APIRouter(prefix="/admin", tags=["admin"])

class SyncBody(BaseModel):
    # incremental: solo novedades desde la última marca guardada (con margen de solape).
    # completa: recorre todo desde 2024-01-01 (lenta; repara huecos).
    modo: Literal["incremental", "completa"] = "incremental"


def _gh():
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPO")
    if not token or not repo:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Sincronización remota no configurada.")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    workflow = os.environ.get("GITHUB_WORKFLOW", "sync.yml")
    return f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}", headers


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
def start_sync(body: SyncBody, admin: dict = Depends(security.require_permission("sincronizar"))):
    url, headers = _gh()
    resp = requests.post(f"{url}/dispatches", headers=headers, timeout=15,
                      json={"ref": os.environ.get("GITHUB_REF", "main"),
                            "inputs": {"modo": body.modo}})
    if resp.status_code != 204:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="GitHub rechazó la solicitud de sincronización.")
    return {"status": "queued", "modo": body.modo}


@router.get("/sync/status")
def sync_status(admin: dict = Depends(security.require_permission("sincronizar"))):
    conn = read_conn()
    try:
        last = db.last_sync(conn)
        total = conn.execute("SELECT COUNT(*) FROM ranking_results").fetchone()[0]
        latest = conn.execute("SELECT MAX(result_date) FROM ranking_results").fetchone()[0]
    finally:
        conn.close()
    result = {"last_sync": dict(last) if last else None, "total_results": total,
              "latest_result_date": latest, "run": None}
    try:
        url, headers = _gh()
        runs = requests.get(f"{url}/runs", headers=headers, params={"per_page": 1}, timeout=15)
        if runs.status_code == 200 and runs.json().get("workflow_runs"):
            r = runs.json()["workflow_runs"][0]
            result["run"] = {"status": r["status"], "conclusion": r["conclusion"],
                             "started_at": r["run_started_at"], "url": r["html_url"]}
    except HTTPException:
        pass  # sin configuración remota: se devuelve solo el estado de la base
    except requests.RequestException:
        pass
    return result


# --- Historial completo de un nadador, por demanda -----------------------------------
def _history_status(swimmer_id: str) -> dict:
    conn = read_conn()
    try:
        st = db.swimmer_history_status(conn, swimmer_id)
    finally:
        conn.close()
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nadador no encontrado.")
    return st


def _fetch_history(swimmer_id: str) -> None:
    try:
        historial.enrich_swimmer(app_conn, swimmer_id)
    except Exception:
        pass


@router.get("/swimmers/{swimmer_id}/historial")
def history_status(swimmer_id: str, admin: dict = Depends(security.require_permission("sincronizar"))):
    return _history_status(swimmer_id)


@router.post("/swimmers/{swimmer_id}/historial", status_code=status.HTTP_202_ACCEPTED)
def fetch_history(swimmer_id: str, background: BackgroundTasks,
                  admin: dict = Depends(security.require_permission("sincronizar"))):
    """Trae de FECNA todo el historial del nadador (tarda de 10 s a 1 min; corre en segundo plano)."""
    st = _history_status(swimmer_id)
    background.add_task(_fetch_history, swimmer_id)
    return st


# --- Roles, permisos y usuarios -----------------------------------------------------
# CRUD de roles y permisos, y asignación de rol a cada usuario. Todo exige «gestionar_usuarios».

import re

_manage = Depends(security.require_permission("gestionar_usuarios"))
_ID = re.compile(r"^[a-z][a-z0-9_]{1,30}$")


class RoleBody(BaseModel):
    role: str


class ActiveBody(BaseModel):
    active: bool


class RoleDef(BaseModel):
    id: str | None = None  # solo al crear: identificador corto (minúsculas, números y _)
    name: str
    permissions: list[str] = []


class PermissionDef(BaseModel):
    key: str | None = None  # solo al crear
    label: str


def _clean_name(value: str, what: str) -> str:
    value = value.strip()
    if not (1 <= len(value) <= 60):
        raise HTTPException(status_code=422, detail=f"{what} no válido (1 a 60 caracteres).")
    return value


@router.get("/roles")
def list_roles(admin: dict = _manage):
    conn = app_conn()
    try:
        return {"roles": db.list_roles(conn), "permissions": db.list_permissions(conn)}
    finally:
        conn.close()


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def create_role(body: RoleDef, admin: dict = _manage):
    rid = (body.id or "").strip().lower()
    if not _ID.match(rid):
        raise HTTPException(status_code=422, detail="Identificador no válido: usa minúsculas, números y _ (2 a 31).")
    name = _clean_name(body.name, "Nombre")
    conn = app_conn()
    try:
        if db.role_exists(conn, rid):
            raise HTTPException(status_code=409, detail="Ya existe un rol con ese identificador.")
        unknown = set(body.permissions) - db.permission_keys(conn)
        if unknown:
            raise HTTPException(status_code=422, detail=f"Permisos desconocidos: {', '.join(sorted(unknown))}.")
        db.save_role(conn, rid, name, body.permissions, create=True)
    finally:
        conn.close()
    security.clear_role_cache()
    return {"id": rid}


@router.put("/roles/{role_id}")
def update_role(role_id: str, body: RoleDef, admin: dict = _manage):
    if role_id == permisos.ADMIN_ROLE:
        raise HTTPException(status_code=409, detail="El rol Administrador no se puede editar: siempre tiene todos los permisos.")
    name = _clean_name(body.name, "Nombre")
    conn = app_conn()
    try:
        if not db.role_exists(conn, role_id):
            raise HTTPException(status_code=404, detail="Rol no encontrado.")
        unknown = set(body.permissions) - db.permission_keys(conn)
        if unknown:
            raise HTTPException(status_code=422, detail=f"Permisos desconocidos: {', '.join(sorted(unknown))}.")
        db.save_role(conn, role_id, name, body.permissions, create=False)
    finally:
        conn.close()
    security.clear_role_cache()
    return {"id": role_id}


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: str, admin: dict = _manage):
    conn = app_conn()
    try:
        roles = {r["id"]: r for r in db.list_roles(conn)}
        role = roles.get(role_id)
        if role is None:
            raise HTTPException(status_code=404, detail="Rol no encontrado.")
        if role["is_system"]:
            raise HTTPException(status_code=409, detail="Los roles Usuario y Administrador no se pueden eliminar.")
        if role["users"]:
            raise HTTPException(status_code=409, detail=f"Hay {role['users']} usuario(s) con este rol: cámbiales el rol antes de eliminarlo.")
        db.delete_role(conn, role_id)
    finally:
        conn.close()
    security.clear_role_cache()


@router.post("/permissions", status_code=status.HTTP_201_CREATED)
def create_permission(body: PermissionDef, admin: dict = _manage):
    key = (body.key or "").strip().lower()
    if not _ID.match(key):
        raise HTTPException(status_code=422, detail="Clave no válida: usa minúsculas, números y _ (2 a 31).")
    label = _clean_name(body.label, "Etiqueta")
    conn = app_conn()
    try:
        if key in db.permission_keys(conn):
            raise HTTPException(status_code=409, detail="Ya existe un permiso con esa clave.")
        db.create_permission(conn, key, label)
    finally:
        conn.close()
    security.clear_role_cache()
    return {"key": key}


@router.put("/permissions/{key}")
def update_permission(key: str, body: PermissionDef, admin: dict = _manage):
    label = _clean_name(body.label, "Etiqueta")
    conn = app_conn()
    try:
        if key not in db.permission_keys(conn):
            raise HTTPException(status_code=404, detail="Permiso no encontrado.")
        db.update_permission_label(conn, key, label)
    finally:
        conn.close()
    return {"key": key}


@router.delete("/permissions/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(key: str, admin: dict = _manage):
    conn = app_conn()
    try:
        perm = next((p for p in db.list_permissions(conn) if p["key"] == key), None)
        if perm is None:
            raise HTTPException(status_code=404, detail="Permiso no encontrado.")
        if perm["is_system"]:
            raise HTTPException(status_code=409, detail="Es un permiso del sistema: el código lo usa y no se puede eliminar (sí puedes cambiar su etiqueta o quitárselo a un rol).")
        db.delete_permission(conn, key)
    finally:
        conn.close()
    security.clear_role_cache()


@router.get("/users")
def list_users(q: str | None = None, limit: int = 50, admin: dict = _manage):
    conn = app_conn()
    try:
        items = db.list_users(conn, q, max(1, min(limit, 100)))
        names = {r["id"]: r["name"] for r in db.list_roles(conn)}
    finally:
        conn.close()
    return {"items": [{**u, "active": bool(u["active"]), "role_name": names.get(u["role"], u["role"])} for u in items]}


@router.put("/users/{user_id}/role")
def set_user_role(user_id: int, body: RoleBody, admin: dict = _manage):
    if str(user_id) == str(admin["id"]):
        raise HTTPException(status_code=409, detail="No puedes cambiar tu propio rol.")
    conn = app_conn()
    try:
        if not db.role_exists(conn, body.role):
            raise HTTPException(status_code=422, detail="Rol no válido.")
        target = db.get_user_by_id(conn, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        if target["role"] == permisos.ADMIN_ROLE and body.role != permisos.ADMIN_ROLE and db.count_active_admins(conn) <= 1:
            raise HTTPException(status_code=409, detail="Debe quedar al menos un administrador.")
        db.set_role(conn, user_id, body.role)
    finally:
        conn.close()
    security.clear_role_cache(user_id)
    return {"id": user_id, "email": target["email"], "role": body.role}


@router.put("/users/{user_id}/active")
def set_user_active(user_id: int, body: ActiveBody, admin: dict = _manage):
    """Activa o desactiva una cuenta (no se borra nada: solo deja de poder entrar)."""
    if str(user_id) == str(admin["id"]):
        raise HTTPException(status_code=409, detail="No puedes desactivar tu propia cuenta.")
    conn = app_conn()
    try:
        target = db.get_user_by_id(conn, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        if (not body.active and target["role"] == permisos.ADMIN_ROLE and target["active"]
                and db.count_active_admins(conn) <= 1):
            raise HTTPException(status_code=409, detail="No se puede desactivar al último administrador activo. "
                                                         "Asigna ese rol a otra cuenta primero.")
        db.set_active(conn, user_id, body.active)
    finally:
        conn.close()
    security.clear_role_cache(user_id)
    return {"id": user_id, "email": target["email"], "active": body.active}
