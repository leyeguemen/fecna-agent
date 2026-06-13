from fecna_agent.aliases import event_aliases


def test_alias_50_libre():
    aliases = event_aliases("50m Libre/50m Free")
    assert "50m Libre/50m Free" in aliases  # nombre oficial siempre presente
    assert "50 libre" in aliases
    assert "50 free" in aliases
    assert "cincuenta libre" in aliases
    assert "50 crol" in aliases


def test_alias_100_espalda():
    aliases = event_aliases("100m Espalda/100m Back")
    assert "100 espalda" in aliases
    assert "cien espalda" in aliases
    assert "100 back" in aliases


def test_relevo():
    aliases = event_aliases("4x50m Libre/4x50m Free Relay")
    assert "4x50 libre" in aliases
    assert "relevo 4x50 libre" in aliases


def test_nombre_sin_estilo_conocido_no_falla():
    assert event_aliases("Prueba rara") == ["Prueba rara"]
