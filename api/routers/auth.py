"""Endpoints de autenticación: registro, login y perfil (/auth/*).

Rate limit básico con slowapi (10/minuto por IP real, ver client_ip) en register/login para
mitigar fuerza bruta. Se puede desactivar en tests con FECNA_RATELIMIT_OFF=1
(leído al construir el limiter, antes de que las pruebas hagan requests)."""

import ipaddress
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from api import security
from api.deps import app_conn
from fecna_agent import auth, db

router = APIRouter(prefix="/auth", tags=["auth"])


def client_ip(request: Request) -> str:
    """IP del cliente para los límites de intentos.

    Render pasa por Cloudflare (`server: cloudflare`, `cf-ray`), que entrega la IP real en
    CF-Connecting-IP y la reescribe en cada petición. Sin él, todos los clientes llegarían con la
    IP del proxy y compartirían un mismo límite. No se usa X-Forwarded-For: Render solo le agrega
    valores, así que el propio cliente puede escribirlo y falsear su IP.
    """
    value = (request.headers.get("cf-connecting-ip") or "").strip()
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return get_remote_address(request)


limiter = Limiter(
    key_func=client_ip,
    enabled=os.environ.get("FECNA_RATELIMIT_OFF") != "1",
)


# Versión vigente de los términos y condiciones (se guarda con la aceptación de cada usuario).
TERMS_VERSION = "2026-11-21"
# Correo para solicitudes sobre la cuenta y los datos (el mismo de los términos, sección 6).
CONTACT_EMAIL = "leoye.work@gmail.com"


class Credentials(BaseModel):
    email: str
    password: str


class RegisterBody(Credentials):
    accept_terms: bool = False  # el cliente nuevo lo exige; los antiguos no lo envían


def _permissions(role: str) -> list[str]:
    conn = app_conn()
    try:
        return db.role_permissions(conn, role)
    finally:
        conn.close()


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, body: RegisterBody):
    admin_emails = auth.parse_admin_emails(os.environ.get("FECNA_ADMIN_EMAIL"))
    role = auth.role_for(body.email, admin_emails)
    conn = app_conn()
    try:
        try:
            user = db.create_user(conn, body.email, body.password, role=role,
                                  terms_version=TERMS_VERSION if body.accept_terms else None)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        conn.close()
    token = security.create_token(user)
    return {"token": token, "email": user["email"], "role": user["role"],
            "permissions": _permissions(user["role"])}


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, body: Credentials):
    conn = app_conn()
    try:
        user, estado = db.check_login(conn, body.email, body.password)
    finally:
        conn.close()
    if estado == "inactive":  # solo con la clave correcta: no revela cuentas a quien no la sabe
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tu cuenta está desactivada. Escribe a {CONTACT_EMAIL} para reactivarla o eliminarla.",
        )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
        )
    token = security.create_token(user)
    return {"token": token, "email": user["email"], "role": user["role"],
            "permissions": _permissions(user["role"])}


@router.get("/me")
def me(user: dict = Depends(security.current_user)):
    access = security.current_access(user)  # rol y permisos vigentes: reflejan cambios de un admin
    if access is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado.")
    return {"email": user["email"], "role": access[0], "permissions": sorted(access[1])}
