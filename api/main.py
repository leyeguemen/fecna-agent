"""Esqueleto de la API FECNA (FastAPI)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import read_conn

app = FastAPI(title="FECNA API")

_origins = os.environ.get("FECNA_CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    conn = read_conn()
    try:
        resultados = conn.execute("SELECT COUNT(*) FROM ranking_results").fetchone()[0]
        nadadores = conn.execute(
            "SELECT COUNT(DISTINCT swimmer_id) FROM ranking_results"
        ).fetchone()[0]
    finally:
        conn.close()
    return {"status": "ok", "resultados": resultados, "nadadores": nadadores}
