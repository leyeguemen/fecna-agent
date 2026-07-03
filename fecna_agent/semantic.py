"""Índice semántico con ChromaDB: pruebas (con alias) y nadadores.

Regla del proyecto: embeddings para encontrar, SQL/Python para calcular.

Embeddings disponibles:
- "hash": bolsa de tokens con hash estable (offline, determinística; suficiente
  para resolver alias y nombres).
- "default": modelo MiniLM de ChromaDB (descarga ~80MB la primera vez).

El nombre del embedding usado se guarda junto al índice para usar el mismo
al consultar.
"""

import re
import unicodedata
import zlib
from pathlib import Path

# ChromaDB es opcional: si no carga (p. ej. incompatibilidad en la nube), la app
# sigue funcionando sin búsqueda semántica. Solo la pestaña "Pregunta" y la
# resolución de nadadores por nombre dependen de él.
try:
    import chromadb
    from chromadb.api.types import EmbeddingFunction

    CHROMADB_AVAILABLE = True
    CHROMADB_IMPORT_ERROR = None
except Exception as exc:  # ImportError u otros (sqlite viejo, protobuf, etc.)
    chromadb = None
    CHROMADB_AVAILABLE = False
    # Guardamos el motivo real para poder diagnosticar en el despliegue.
    CHROMADB_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

    class EmbeddingFunction:  # base de respaldo para definir la clase de abajo
        pass


DEFAULT_PERSIST_DIR = Path(__file__).resolve().parent.parent / "data" / "chroma"
EMBEDDING_MARKER = "embedding.txt"

EVENTS_COLLECTION = "events"
SWIMMERS_COLLECTION = "swimmers"


class HashEmbeddingFunction(EmbeddingFunction):
    """Bolsa de tokens con hash CRC32 (estable entre procesos)."""

    DIM = 256

    def __init__(self):
        pass

    def __call__(self, input):
        return [self._embed(text) for text in input]

    @staticmethod
    def name() -> str:
        return "hash-bow"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "HashEmbeddingFunction":
        return HashEmbeddingFunction()

    @classmethod
    def _embed(cls, text: str) -> list[float]:
        vector = [0.0] * cls.DIM
        for token in _tokens(text):
            vector[zlib.crc32(token.encode()) % cls.DIM] += 1.0
        norm = sum(v * v for v in vector) ** 0.5
        if norm == 0:
            vector[0] = 1.0
            return vector
        return [v / norm for v in vector]


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.findall(r"[a-z0-9]+", text)


def get_embedding_fn(name: str):
    if name == "hash":
        return HashEmbeddingFunction()
    if name == "default":
        return None  # ChromaDB usa su embedding por defecto (MiniLM)
    raise ValueError(f"Embedding desconocido: {name!r}")


def get_client(persist_dir: Path | str | None = DEFAULT_PERSIST_DIR):
    if not CHROMADB_AVAILABLE:
        return None
    if persist_dir is None:
        return chromadb.EphemeralClient()
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def save_embedding_name(persist_dir: Path | str, name: str) -> None:
    (Path(persist_dir) / EMBEDDING_MARKER).write_text(name)


def load_embedding_name(persist_dir: Path | str | None) -> str:
    if persist_dir is None:
        return "hash"
    marker = Path(persist_dir) / EMBEDDING_MARKER
    return marker.read_text().strip() if marker.exists() else "hash"


def _recreate(client, name: str, embedding_fn):
    try:
        client.delete_collection(name)
    except Exception:
        pass
    kwargs = {"metadata": {"hnsw:space": "cosine"}}
    if embedding_fn is not None:
        kwargs["embedding_function"] = embedding_fn
    return client.create_collection(name, **kwargs)


def index_events(client, events: list[tuple[str, str]], embedding: str = "hash") -> int:
    """Indexa pruebas con sus alias. events = [(event_id, event_name), ...].
    Devuelve cuántos documentos (alias) se indexaron."""
    from .aliases import event_aliases

    if client is None:
        return 0
    collection = _recreate(client, EVENTS_COLLECTION, get_embedding_fn(embedding))
    ids, documents, metadatas = [], [], []
    for event_id, event_name in events:
        for i, alias in enumerate(event_aliases(event_name)):
            ids.append(f"{event_id}-{i}")
            documents.append(alias)
            metadatas.append({"event_id": event_id, "event_name": event_name})
    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def index_swimmers(client, swimmers: list[tuple[str, str]], embedding: str = "hash") -> int:
    """Indexa nadadores por nombre. swimmers = [(swimmer_id, name), ...]."""
    if client is None:
        return 0
    collection = _recreate(client, SWIMMERS_COLLECTION, get_embedding_fn(embedding))
    if swimmers:
        collection.add(
            ids=[sid for sid, _ in swimmers],
            documents=[name for _, name in swimmers],
            metadatas=[{"swimmer_id": sid, "swimmer_name": name} for sid, name in swimmers],
        )
    return len(swimmers)


def _query_candidates(client, collection_name: str, text: str, embedding: str,
                      n: int = 5) -> list[tuple[dict, str]]:
    """Vecinos más cercanos: [(metadata, documento), ...] (puede ser vacío)."""
    if client is None:
        return []
    kwargs = {}
    fn = get_embedding_fn(embedding)
    if fn is not None:
        kwargs["embedding_function"] = fn
    try:
        collection = client.get_collection(collection_name, **kwargs)
    except Exception:
        return []
    result = collection.query(query_texts=[text], n_results=n,
                              include=["metadatas", "documents"])
    metadatas = (result.get("metadatas") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    return list(zip(metadatas, documents))


def _name_score(query: str, name: str) -> float:
    """Fracción de tokens de la consulta presentes en el nombre.

    El vecino más cercano del índice puede estar lejísimos (ChromaDB siempre
    devuelve algo); esta validación léxica evita responder con un nadador que
    no tiene nada que ver con lo preguntado. Acepta prefijos (≥4 letras) para
    tolerar nombres escritos a medias ("gonza" → GONZALEZ)."""
    q_tokens = _tokens(query)
    if not q_tokens:
        return 0.0
    name_tokens = _tokens(name)
    hits = sum(
        1 for t in q_tokens
        if any(w == t or (len(t) >= 4 and w.startswith(t)) for w in name_tokens)
    )
    return hits / len(q_tokens)


def rebuild_from_db(conn, embedding: str = "hash", persist_dir=DEFAULT_PERSIST_DIR) -> str:
    """Reconstruye el índice completo (pruebas y nadadores) desde la base local."""
    from . import db as database

    if not CHROMADB_AVAILABLE:
        return "ChromaDB no disponible: búsqueda semántica desactivada."
    events = database.get_catalog(conn, "prueba")
    if not events:
        return "No hay catálogo de pruebas. Ejecuta primero: python -m fecna_agent catalog"
    client = get_client(persist_dir)
    n_aliases = index_events(client, events, embedding)
    n_swimmers = index_swimmers(client, database.list_swimmers(conn), embedding)
    save_embedding_name(persist_dir, embedding)
    return (f"Indexados: {len(events)} pruebas ({n_aliases} alias), "
            f"{n_swimmers} nadadores [embeddings: {embedding}]")


def resolve_event(client, text: str, embedding: str = "hash") -> dict | None:
    """Mejor prueba para el texto: {'event_id', 'event_name'} o None.

    Solo acepta el resultado si el alias coincidente aparece de verdad en el
    texto (por tokens): una pregunta que no menciona ninguna prueba devuelve
    None en vez de un evento arbitrario."""
    candidates = _query_candidates(client, EVENTS_COLLECTION, text, embedding, n=1)
    if not candidates:
        return None
    metadata, document = candidates[0]
    query_tokens = set(_tokens(text))
    doc_tokens = _tokens(document)
    if doc_tokens and all(t in query_tokens for t in doc_tokens):
        return metadata
    return None


def resolve_swimmer_candidates(client, text: str, embedding: str = "hash",
                               n: int = 5, min_score: float = 0.6) -> list[dict]:
    """Nadadores que coinciden con el texto, validados léxicamente.

    Devuelve [{'swimmer_id', 'swimmer_name', 'score'}, ...] ordenados por score
    descendente. Vacío si nadie supera min_score (el texto no es un nombre de
    la base). Si hay varios con el mismo score máximo son homónimos y quien
    llama debe pedir desambiguación."""
    from .resolver import extract_name_query

    query = extract_name_query(text) or text
    scored = []
    for metadata, _doc in _query_candidates(client, SWIMMERS_COLLECTION, query,
                                            embedding, n=n):
        score = _name_score(query, metadata.get("swimmer_name", ""))
        if score >= min_score:
            scored.append({**metadata, "score": score})
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored


def resolve_swimmer(client, text: str, embedding: str = "hash") -> dict | None:
    """Mejor nadador para el texto: {'swimmer_id', 'swimmer_name'} o None."""
    candidates = resolve_swimmer_candidates(client, text, embedding)
    return candidates[0] if candidates else None
