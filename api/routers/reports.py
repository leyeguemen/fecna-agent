"""Reportes de problemas desde la app → issue público en GitHub.

El servidor no crea el issue directamente: dispara el workflow «reporte.yml» (workflow_dispatch) con
el token que ya usa para la sincronización, de modo que ese token no necesita permiso de Issues.
Variables: GITHUB_TOKEN (permiso Actions: read/write), GITHUB_REPO y GITHUB_REF (por defecto main).

Como el repositorio es público, el reporte lo ve cualquiera: no se adjunta el correo ni el id del
usuario, y se advierte en la app que no incluyan datos personales.
"""

import os
import re
import time

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from api import security
from api.routers.auth import limiter

router = APIRouter(prefix="/reports", tags=["reports"])

_DAILY_LIMIT = 10
_sent: dict[tuple, int] = {}
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class ReportBody(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    screen: str | None = Field(default=None, max_length=40)
    platform: str | None = Field(default=None, max_length=20)
    app_version: str | None = Field(default=None, max_length=20)


def _clean(text: str) -> str:
    """Sin caracteres de control y sin @menciones activas (no notificar a terceros)."""
    return _CONTROL.sub("", text).replace("@", "@\u200b").strip()


def _check_daily_limit(user_id) -> None:
    key = (str(user_id), time.strftime("%Y-%m-%d"))
    for old in [k for k in _sent if k[1] != key[1]]:
        _sent.pop(old, None)
    if _sent.get(key, 0) >= _DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Ya enviaste varios reportes hoy. Intenta mañana.")
    _sent[key] = _sent.get(key, 0) + 1


@router.post("", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/hour")
def create_report(request: Request, body: ReportBody,
                  user: dict = Depends(security.require_permission("reportar_problema"))):
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPO")
    if not token or not repo:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Los reportes no están configurados.")
    _check_daily_limit(user["id"])
    title = _clean(" ".join(body.title.split()))
    lines = [_clean(body.description), "", "---",
             f"Reportado desde la app · pantalla: {_clean(body.screen or 'no indicada')} · "
             f"dispositivo: {_clean(body.platform or 'no indicado')} · versión: {_clean(body.app_version or 'no indicada')} · "
             f"rol: {user['role']}"]
    labels = "bug,desde-la-app" + (",android" if (body.platform or "").lower() == "android" else
                                   ",iphone-web" if (body.platform or "").lower() in ("web", "ios") else "")
    resp = requests.post(
        f"https://api.github.com/repos/{repo}/actions/workflows/reporte.yml/dispatches",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        json={"ref": os.environ.get("GITHUB_REF", "main"),
              "inputs": {"titulo": f"[App] {title}", "cuerpo": "\n".join(lines), "etiquetas": labels}},
        timeout=15,
    )
    if resp.status_code != 204:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No se pudo enviar el reporte. Intenta de nuevo.")
    return {"status": "queued"}
