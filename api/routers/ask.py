"""Endpoint conversacional del agente (POST /ask).

Delega en `fecna_agent.agent.chat_answer` (determinístico, sin LLM) sobre la
base de LECTURA (pública, anonimizada). Reutiliza el mismo limiter que
/auth para acotar el uso. Si la búsqueda semántica (ChromaDB) falla, se
responde 503 en vez de romper la petición: el resto de la app no depende
de ella."""

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from api.deps import read_conn
from api.routers.auth import limiter
from fecna_agent import agent, semantic

router = APIRouter(tags=["ask"])


class AskBody(BaseModel):
    question: str
    context: dict | None = None


@router.post("/ask")
@limiter.limit("30/minute")
def ask(request: Request, body: AskBody):
    conn = read_conn()
    try:
        reply, new_context = agent.chat_answer(
            conn, body.question, context=body.context, persist_dir=semantic.DEFAULT_PERSIST_DIR
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Búsqueda semántica no disponible.",
        ) from exc
    finally:
        conn.close()
    return {"reply": reply, "context": new_context}
