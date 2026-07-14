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


def require_admin(user: dict = Depends(current_user)) -> dict:
    """Dependencia FastAPI: exige rol admin o lanza 403."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol de administrador.",
        )
    return user
