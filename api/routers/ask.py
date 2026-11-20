"""Endpoint conversacional del agente (POST /ask).

Delega en `fecna_agent.agent.chat_answer` (determinístico, sin LLM) sobre la
base de LECTURA (pública, anonimizada). Reutiliza el mismo limiter que
/auth para acotar el uso. Si la búsqueda semántica (ChromaDB) falla, se
responde 503 en vez de romper la petición: el resto de la app no depende
de ella."""

import os
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from api import security
from api.deps import read_conn
from api.routers.auth import limiter
from fecna_agent import agent, claude_agent, semantic

router = APIRouter(tags=["ask"])


_usage: dict[tuple[str, str], int] = defaultdict(int)  # (usuario, día) -> preguntas


def _check_daily_limit(user_id: str) -> None:
    """Tope diario por usuario para acotar el costo de la API de Claude."""
    limit = int(os.environ.get("FECNA_ASK_DAILY_LIMIT", "50"))
    key = (str(user_id), date.today().isoformat())
    if _usage[key] >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Alcanzaste el límite diario de preguntas.")
    _usage[key] += 1


class AskBody(BaseModel):
    question: str
    context: dict | None = None
    history: list[dict] | None = None  # turnos previos [{role, content}] (solo con Claude)


@router.post("/ask")
@limiter.limit("30/minute")
def ask(request: Request, body: AskBody, user: dict = Depends(security.current_user)):
    if os.environ.get("ANTHROPIC_API_KEY"):
        _check_daily_limit(user["id"])
        conn = read_conn()
        try:
            reply = claude_agent.answer(conn, body.question, body.history)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="El asistente no está disponible.") from exc
        finally:
            conn.close()
        return {"reply": reply, "context": None}
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
