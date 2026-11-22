"""JWT: creación/verificación de tokens y dependencias FastAPI de autenticación.

El secreto se lee de FECNA_JWT_SECRET en cada llamada (no al importar), para
que los tests puedan usar monkeypatch. Si la variable no está definida (modo
dev), se usa un secreto aleatorio generado una sola vez al importar este
módulo: los tokens dejan de ser válidos al reiniciar el proceso, lo cual es
aceptable en desarrollo. En producción FECNA_JWT_SECRET es obligatoria para
que los tokens sobrevivan a reinicios/redeploys.
"""

import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("fecna.api")

_ALGORITHM = "HS256"
_EXPIRATION = timedelta(days=7)
# Fallback de desarrollo: generado una sola vez por proceso.
_dev_fallback_secret = secrets.token_hex(32)
_fallback_warned = False

_bearer_scheme = HTTPBearer(auto_error=False)


def _secret() -> str:
    global _fallback_warned
    secret = os.environ.get("FECNA_JWT_SECRET")
    if secret:
        return secret
    if not _fallback_warned:
        logger.warning(
            "FECNA_JWT_SECRET no está configurado: se usa un secreto aleatorio; "
            "las sesiones se invalidarán en cada reinicio."
        )
        _fallback_warned = True
    return _dev_fallback_secret


def create_token(user) -> str:
    """Genera un token JWT HS256 para el usuario (dict o sqlite3.Row)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "exp": now + _EXPIRATION,
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """Dependencia FastAPI: decodifica el Bearer token o lanza 401."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado.")
    try:
        payload = jwt.decode(credentials.credentials, _secret(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado.")
    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role"),
    }


# --- Rol vigente y permisos ---------------------------------------------------------
# El token lleva el rol con el que se inició sesión (dura 7 días). Para las acciones de
# administrador se consulta el rol actual en la base (con una caché corta), de modo que quitar
# un rol o borrar una cuenta surta efecto en segundos y no al vencer el token.
_ROLE_TTL = 30  # segundos
_ROLE_CACHE: dict[tuple, tuple[float, str | None]] = {}


def _cache_scope() -> str:
    return os.environ.get("DATABASE_URL") or os.environ.get("TURSO_DATABASE_URL") \
        or os.environ.get("FECNA_APP_DB", "data/fecna_app.db")


def clear_role_cache(user_id=None) -> None:
    """Olvida el rol en caché (de un usuario, o de todos)."""
    if user_id is None:
        _ROLE_CACHE.clear()
    else:
        for key in [k for k in _ROLE_CACHE if k[1] == str(user_id)]:
            _ROLE_CACHE.pop(key, None)


def current_role(user: dict) -> str | None:
    """Rol vigente del usuario en la base, o None si ya no existe o está inactivo."""
    from api.deps import app_conn
    from fecna_agent import db

    key = (_cache_scope(), str(user.get("id")))
    hit = _ROLE_CACHE.get(key)
    if hit and time.monotonic() - hit[0] < _ROLE_TTL:
        return hit[1]
    try:
        uid = int(user.get("id"))
    except (TypeError, ValueError):
        return None
    conn = app_conn()
    try:
        row = db.get_user_by_id(conn, uid)
    finally:
        conn.close()
    role = row["role"] if row and row["active"] else None
    _ROLE_CACHE[key] = (time.monotonic(), role)
    return role


def require_permission(permission: str, fresh: bool = True):
    """Dependencia FastAPI: exige el permiso o lanza 403 (401 si la cuenta ya no existe).

    fresh=True consulta el rol vigente en la base; fresh=False usa el rol del token (sin
    consultar), para permisos que tienen todos los usuarios."""
    from fecna_agent import permisos

    def dependency(user: dict = Depends(current_user)) -> dict:
        role = current_role(user) if fresh else user.get("role")
        if role is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado.")
        if not permisos.has(role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="No tienes permiso para esta acción.")
        return {**user, "role": role}

    return dependency
