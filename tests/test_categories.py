from fecna_agent.categories import age_range


def test_categoria_de_un_anio():
    assert age_range("12 AÑOS") == (12, 12)


def test_categoria_de_rango():
    assert age_range("10 Y 11 Infantil A") == (10, 11)
    assert age_range("7 a 9 Menores") == (7, 9)
    assert age_range("25-29") == (25, 29)


def test_categoria_abierta():
    assert age_range("21 Y MAS - Cat Mayores") == (21, 999)
    assert age_range("95 y/o Más") == (95, 999)


def test_sin_numeros():
    assert age_range("Mayores") is None
