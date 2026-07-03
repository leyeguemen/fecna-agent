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
    assert q.event_query == "50 libre"
    assert q.pool_type is None


def test_extrae_prueba_con_metros_y_id_largo():
    q = parse_question("Mejor tiempo del nadador 1080063221 en 800m Libre")
    assert q.intent == "best"
    assert q.swimmer_ids == ["1080063221"]
    assert q.event_query == "800 libre"


def test_extrae_prueba_en_palabras():
    q = parse_question("mejor marca en ochocientos libre")
    assert q.event_query == "800 libre"


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


def test_intents_ampliados():
    assert parse_question("¿quién es el más rápido en 50 libre?").intent == "ranking"
    assert parse_question("¿cómo va Juan Pérez en 100 pecho?").intent == "history"
    assert parse_question("récord de 1105388915 en 50 libre").intent == "best"


def test_explicit_intent_marca_si_se_entendio_la_intencion():
    assert parse_question("ranking 50 libre").explicit_intent is True
    assert parse_question("1105388915 y 1094060609 en 50 libre").explicit_intent is True
    assert parse_question("hola, ¿qué puedes hacer?").explicit_intent is False


def test_extrae_nombre_del_nadador():
    q = parse_question("¿cuál es la mejor marca de Juan Pérez en 100 espalda piscina corta?")
    assert q.name_query == "juan perez"
    q = parse_question("evolución de maria camila torres en cincuenta libre")
    assert q.name_query == "maria camila torres"


def test_nombre_none_si_solo_hay_id_prueba_o_saludo():
    assert parse_question("mejor marca de 1105388915 en 50 libre").name_query is None
    assert parse_question("ranking femenino de 12 años en 50 libre").name_query is None
    assert parse_question("hola, ¿qué puedes hacer?").name_query is None
