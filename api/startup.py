"""Arranque de la API: reconstruye el índice semántico si falta.

En despliegues donde solo se sube `data/fecna_public.db` (p. ej. HF Spaces,
donde `data/chroma/` está en `.gitignore` y no viaja con el repo), el índice
de ChromaDB no existe en la imagen. Se reconstruye una sola vez al arrancar,
con la misma lógica que `fecna_agent.webui.ensure_semantic_index` pero sin el
cache de Streamlit (aquí se ejecuta una vez en el evento de startup de
FastAPI). Cualquier fallo (ChromaDB no disponible, base vacía, etc.) se
registra como advertencia y no impide que la API arranque: /ask simplemente
responderá 503 si la búsqueda semántica no está lista."""

import logging

from api.deps import read_conn
from fecna_agent import db as database
from fecna_agent import semantic

logger = logging.getLogger("fecna.api.startup")


def ensure_semantic_index() -> None:
    try:
        client = semantic.get_client()
        if client is not None and client.get_collection(semantic.EVENTS_COLLECTION).count() > 0:
            return  # el índice ya existe (p. ej. se copió junto con la imagen)
    except Exception:
        pass  # sin colección todavía: seguimos e intentamos reconstruirlo

    conn = read_conn()
    try:
        if database.get_catalog(conn, "prueba") and database.list_events(conn):
            resultado = semantic.rebuild_from_db(conn)
            logger.info("Índice semántico: %s", resultado)
        else:
            logger.warning(
                "No se reconstruyó el índice semántico: la base de lectura "
                "no tiene catálogo ni eventos."
            )
    except Exception as exc:
        logger.warning("No se pudo reconstruir el índice semántico: %s", exc)
    finally:
        conn.close()
