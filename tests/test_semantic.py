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
    # Homónimos para probar la desambiguación:
    ("111", "JUAN PEREZ GOMEZ"),
    ("222", "JUAN PEREZ LOPEZ"),
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


def test_no_inventa_nadador_inexistente(client):
    # Antes devolvía el vecino más cercano aunque no tuviera nada que ver.
    assert semantic.resolve_swimmer(client, "pedro picapiedra") is None


def test_no_inventa_prueba_si_no_se_menciona(client):
    # Una pregunta sin prueba no debe resolver a un evento arbitrario.
    assert semantic.resolve_event(client, "mejor marca de jorge murillo") is None


def test_candidatos_homonimos(client):
    cands = semantic.resolve_swimmer_candidates(client, "juan perez")
    assert {c["swimmer_id"] for c in cands} == {"111", "222"}


def test_nombre_mas_especifico_desambigua_solo(client):
    cands = semantic.resolve_swimmer_candidates(client, "juan perez gomez")
    assert cands[0]["swimmer_id"] == "111"
    assert len([c for c in cands if c["score"] == cands[0]["score"]]) == 1
