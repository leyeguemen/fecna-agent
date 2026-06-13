from fecna_agent.normalizer import normalize_rows

RAW = {
    "tiempo": "00:00:28.84",
    "identificacion": "1105388915",
    "prueba_id": "2",
    "piscina": "LC",
    "nombre_liga": "COLOMBIA",
    "prueba": "50m Libre/50m Free",
    "fecha_nac": "2014-08-03",
    "nombre_club": "COLOMBIA",
    "nombre": "JORGE MARIO",
    "apellido": "MURILLO GALLEGO",
    "genero": "M",
    "contador": 1,
    "puntos": 381,
    "fecha_tor": "2026-03-25",
    "nada": "JORGE MARIO MURILLO GALLEGO",
    "edad": "2014-08",
}


def test_normaliza_registro_del_spec():
    rows = normalize_rows([RAW])
    assert len(rows) == 1
    row = rows[0]
    assert row["swimmer_id"] == "1105388915"
    assert row["swimmer_name"] == "JORGE MARIO MURILLO GALLEGO"
    assert row["time_ms"] == 28840
    assert row["event_id"] == "2"
    assert row["pool_type"] == "LC"
    assert row["points"] == 381
    assert row["fetched_at"]


def test_descarta_registro_invalido_sin_abortar():
    invalido = dict(RAW, tiempo="basura")
    rows = normalize_rows([RAW, invalido])
    assert len(rows) == 1
