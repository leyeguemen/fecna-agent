"""Endpoints de administración: disparar y consultar la sincronización del ranking.

La sincronización corre en GitHub Actions (workflow_dispatch) y escribe en
Postgres. Variables: GITHUB_TOKEN (fine-grained, permiso Actions: read/write),
GITHUB_REPO ("usuario/repo"), GITHUB_WORKFLOW (defecto sync.yml), GITHUB_REF (defecto main).
"""

import os
import re

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api import security
from api.deps import read_conn
from fecna_agent import db

router = APIRouter(prefix="/admin", tags=["admin"])

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SyncBody(BaseModel):
    inicio: str  # YYYY-MM-DD


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
def start_sync(body: SyncBody, admin: dict = Depends(security.require_admin)):
    if not _DATE.match(body.inicio):
        raise HTTPException(status_code=422, detail="Fecha inválida (usa YYYY-MM-DD).")
    url, headers = _gh()
    resp = requests.post(f"{url}/dispatches", headers=headers, timeout=15,
                      json={"ref": os.environ.get("GITHUB_REF", "main"),
                            "inputs": {"inicio": body.inicio}})
    if resp.status_code != 204:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="GitHub rechazó la solicitud de sincronización.")
    return {"status": "queued", "inicio": body.inicio}


@router.get("/sync/status")
def sync_status(admin: dict = Depends(security.require_admin)):
    conn = read_conn()
    try:
        last = db.last_sync(conn)
        total = conn.execute("SELECT COUNT(*) FROM ranking_results").fetchone()[0]
    finally:
        conn.close()
    result = {"last_sync": dict(last) if last else None, "total_results": total, "run": None}
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
