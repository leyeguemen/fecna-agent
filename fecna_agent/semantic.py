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

import chromadb
from chromadb.api.types import EmbeddingFunction

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
    if persist_dir is None:
        return chromadb.EphemeralClient()
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def save_embedding_name(persist_dir: Path | str, name: str) -> None:
    (Path(persist_dir) / EMBEDDING_MARKER).write_text(name)


def load_embedding_name(persist_dir: Path | str) -> str:
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
    collection = _recreate(client, SWIMMERS_COLLECTION, get_embedding_fn(embedding))
    if swimmers:
        collection.add(
            ids=[sid for sid, _ in swimmers],
            documents=[name for _, name in swimmers],
            metadatas=[{"swimmer_id": sid, "swimmer_name": name} for sid, name in swimmers],
        )
    return len(swimmers)


def _resolve(client, collection_name: str, text: str, embedding: str) -> dict | None:
    kwargs = {}
    fn = get_embedding_fn(embedding)
    if fn is not None:
        kwargs["embedding_function"] = fn
    try:
        collection = client.get_collection(collection_name, **kwargs)
    except Exception:
        return None
    result = collection.query(query_texts=[text], n_results=1)
    metadatas = result.get("metadatas") or [[]]
    return metadatas[0][0] if metadatas[0] else None


def rebuild_from_db(conn, embedding: str = "hash", persist_dir=DEFAULT_PERSIST_DIR) -> str:
    """Reconstruye el índice completo (pruebas y nadadores) desde la base local."""
    from . import db as database

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
    """Mejor prueba para el texto: {'event_id', 'event_name'} o None."""
    return _resolve(client, EVENTS_COLLECTION, text, embedding)


def resolve_swimmer(client, text: str, embedding: str = "hash") -> dict | None:
    """Mejor nadador para el texto: {'swimmer_id', 'swimmer_name'} o None."""
    return _resolve(client, SWIMMERS_COLLECTION, text, embedding)
