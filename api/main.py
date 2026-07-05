"""Esqueleto de la API FECNA (FastAPI)."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.deps import read_conn
from api.routers import ask as ask_router
from api.routers import auth as auth_router
from api.routers import competitions as competitions_router
from api.routers import rankings as rankings_router
from api.routers import swimmers as swimmers_router
from api.startup import ensure_semantic_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Reconstruye el índice semántico si falta (p. ej. imagen de despliegue
    # sin `data/chroma/`, que está en .gitignore). No bloquea el arranque si
    # falla: /ask responde 503 en ese caso.
    ensure_semantic_index()
    yield


app = FastAPI(title="FECNA API", lifespan=lifespan)

app.state.limiter = auth_router.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS se agrega al final para quedar como middleware más externo (envuelve a
# SlowAPI también), así los headers CORS llegan incluso en respuestas 429.
_origins = os.environ.get("FECNA_CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(rankings_router.router)
app.include_router(swimmers_router.router)
app.include_router(competitions_router.router)
app.include_router(ask_router.router)


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
