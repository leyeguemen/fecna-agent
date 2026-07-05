"""Endpoints de autenticación: registro, login y perfil (/auth/*).

Rate limit básico con slowapi (10/minuto por IP) en register/login para
mitigar fuerza bruta. Se puede desactivar en tests con FECNA_RATELIMIT_OFF=1
(leído al construir el limiter, antes de que las pruebas hagan requests)."""

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from api import security
from api.deps import app_conn
from fecna_agent import auth, db

router = APIRouter(prefix="/auth", tags=["auth"])

limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.environ.get("FECNA_RATELIMIT_OFF") != "1",
)


class Credentials(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, body: Credentials):
    admin_emails = auth.parse_admin_emails(os.environ.get("FECNA_ADMIN_EMAIL"))
    role = auth.role_for(body.email, admin_emails)
    conn = app_conn()
    try:
        try:
            user = db.create_user(conn, body.email, body.password, role=role)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        conn.close()
    token = security.create_token(user)
    return {"token": token, "email": user["email"], "role": user["role"]}


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, body: Credentials):
    conn = app_conn()
    try:
        user = db.authenticate(conn, body.email, body.password)
    finally:
        conn.close()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
        )
    token = security.create_token(user)
    return {"token": token, "email": user["email"], "role": user["role"]}


@router.get("/me")
def me(user: dict = Depends(security.current_user)):
    return {"email": user["email"], "role": user["role"]}
