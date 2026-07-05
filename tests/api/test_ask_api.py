"""Tests de POST /ask (endpoint conversacional del agente)."""

import pytest
from fastapi.testclient import TestClient

from fecna_agent import agent, db, semantic


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "read.db"
    db.connect(db_path).close()
    monkeypatch.setenv("FECNA_DB", str(db_path))

    from api import main

    return TestClient(main.app)


def test_ask_pasa_pregunta_y_contexto_al_agente(client, monkeypatch):
    """El endpoint delega en agent.chat_answer y expone su resultado tal cual."""
    captured = {}

    def fake_chat_answer(conn, question, context=None, persist_dir=None):
        captured["question"] = question
        captured["context"] = context
        return "respuesta de prueba", {"swimmer_ids": ["1"], "event_query": "50 libre",
                                        "pool_type": "LC", "gender": None}

    monkeypatch.setattr(agent, "chat_answer", fake_chat_answer)

    resp = client.post("/ask", json={"question": "¿cómo va?", "context": {"swimmer_ids": ["1"]}})

    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "respuesta de prueba"
    assert body["context"]["event_query"] == "50 libre"
    assert captured["question"] == "¿cómo va?"
    assert captured["context"] == {"swimmer_ids": ["1"]}


def test_ask_sin_contexto_previo(client, monkeypatch):
    def fake_chat_answer(conn, question, context=None, persist_dir=None):
        assert context is None
        return "ok", {"swimmer_ids": [], "event_query": None, "pool_type": None, "gender": None}

    monkeypatch.setattr(agent, "chat_answer", fake_chat_answer)

    resp = client.post("/ask", json={"question": "hola"})
    assert resp.status_code == 200
    assert resp.json()["reply"] == "ok"


def test_ask_responde_ayuda_deterministica_sin_chroma(client, monkeypatch):
    """Sin ChromaDB disponible, el agente sigue respondiendo (mensaje de ayuda)."""
    monkeypatch.setattr(semantic, "get_client", lambda *a, **k: None)

    resp = client.post("/ask", json={"question": "hola, ¿qué puedes hacer?"})

    assert resp.status_code == 200
    body = resp.json()
    assert "ranking" in body["reply"].lower()
    assert "compara" in body["reply"].lower()
    assert body["context"] == {
        "swimmer_ids": [], "event_query": None, "pool_type": None, "gender": None,
    }


def test_ask_semantica_no_disponible_devuelve_503(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("chroma roto")

    monkeypatch.setattr(agent, "chat_answer", boom)

    resp = client.post("/ask", json={"question": "hola"})

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Búsqueda semántica no disponible."
