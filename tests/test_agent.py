from fecna_agent.agent import _merge_context
from fecna_agent.resolver import parse_question


def ctx(**kw):
    base = {"swimmer_ids": [], "event_query": None, "pool_type": None, "gender": None}
    base.update(kw)
    return base


def test_hereda_nadador_evento_y_piscina_en_seguimiento():
    p = _merge_context(parse_question("y su evolución"),
                       ctx(swimmer_ids=["111111"], event_query="50 libre", pool_type="LC"))
    assert p.swimmer_ids == ["111111"]   # pronombre "su" → hereda nadador
    assert p.event_query == "50 libre"
    assert p.pool_type == "LC"
    assert p.intent == "history"


def test_no_hereda_nadador_sin_pronombre():
    p = _merge_context(parse_question("ranking de 100 libre"), ctx(swimmer_ids=["111111"]))
    assert p.swimmer_ids == []           # no secuestra el contexto
    assert p.event_query == "100 libre"  # el evento explícito manda


def test_compare_completa_el_par_desde_el_contexto():
    p = _merge_context(parse_question("compáralo con 222222"), ctx(swimmer_ids=["111111"]))
    assert set(p.swimmer_ids) == {"111111", "222222"}
    assert p.intent == "compare"


def test_pregunta_explicita_ignora_el_contexto():
    p = _merge_context(parse_question("mejor marca de 999999 en 200 espalda"),
                       ctx(swimmer_ids=["111111"], event_query="50 libre", pool_type="LC"))
    assert p.swimmer_ids == ["999999"]
    assert p.event_query == "200 espalda"


def test_sin_contexto_no_cambia_nada():
    p = _merge_context(parse_question("ranking 50 libre"), ctx())
    assert p.swimmer_ids == []
    assert p.event_query == "50 libre"
