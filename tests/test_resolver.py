from fecna_agent.resolver import parse_question


def test_pregunta_compare_del_spec():
    q = parse_question(
        "Compara el nadador 1105388915 con el nadador 1094060609 en 50 libre piscina larga."
    )
    assert q.intent == "compare"
    assert q.swimmer_ids == ["1105388915", "1094060609"]
    assert q.pool_type == "LC"


def test_mejor_marca():
    q = parse_question("¿Cuál es la mejor marca del nadador 1105388915 en 50 libre?")
    assert q.intent == "best"
    assert q.swimmer_ids == ["1105388915"]
    assert q.pool_type is None


def test_ranking_con_genero_y_categoria():
    q = parse_question("Muéstrame el ranking masculino de 12 años en 50 libre piscina larga.")
    assert q.intent == "ranking"
    assert q.gender == "M"
    assert q.category == "12 AÑOS"
    assert q.pool_type == "LC"


def test_evolucion():
    q = parse_question("¿Cuál es la evolución de este nadador desde 2024?")
    assert q.intent == "history"


def test_dos_ids_sin_verbo_es_compare():
    q = parse_question("1105388915 y 1094060609 en 50 libre")
    assert q.intent == "compare"


def test_piscina_corta():
    q = parse_question("mejor tiempo de 1105388915 en piscina corta")
    assert q.pool_type == "SC"
