import pytest

from fecna_agent import semantic

EVENTS = [
    ("2", "50m Libre/50m Free"),
    ("4", "100m Espalda/100m Back"),
    ("6", "800m Libre/800m Free"),
]

SWIMMERS = [
    ("1105388915", "JORGE MARIO MURILLO GALLEGO"),
    ("1094060609", "SANTIAGO HERRERA SABOGAL"),
]


@pytest.fixture(scope="module")
def client():
    client = semantic.get_client(persist_dir=None)  # efímero, en memoria
    semantic.index_events(client, EVENTS, embedding="hash")
    semantic.index_swimmers(client, SWIMMERS, embedding="hash")
    return client


def test_resuelve_alias_de_prueba(client):
    assert semantic.resolve_event(client, "cincuenta libre")["event_id"] == "2"
    assert semantic.resolve_event(client, "100 espalda")["event_id"] == "4"
    assert semantic.resolve_event(client, "ochocientos libre")["event_id"] == "6"


def test_resuelve_pregunta_completa(client):
    match = semantic.resolve_event(
        client, "Compara el nadador 1105388915 con el 1094060609 en 50 libre piscina larga"
    )
    assert match["event_id"] == "2"


def test_resuelve_nadador_por_nombre_aproximado(client):
    match = semantic.resolve_swimmer(client, "mejor marca de jorge murillo")
    assert match["swimmer_id"] == "1105388915"


def test_embedding_estable_entre_llamadas():
    embed = semantic.HashEmbeddingFunction._embed
    assert embed("50 libre") == embed("50 libre")
    assert embed("50 libre") == embed("Cincuenta LIBRE".lower().replace("cincuenta", "50"))
