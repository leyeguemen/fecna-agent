from fecna_agent.catalog import parse_catalogs

HTML = """
<form>
  <select name="prueba">
    <option value="">Todas</option>
    <option value="2">50m Libre/50m Free</option>
    <option value="6">800m Libre/800m Free</option>
  </select>
  <select name="categoria[]" multiple>
    <option value="12 AÑOS">12 AÑOS</option>
    <option value="13 AÑOS">13 AÑOS</option>
  </select>
  <select name="piscina">
    <option value="LC">Larga</option>
    <option value="SC">Corta</option>
  </select>
</form>
"""


def test_parse_selects():
    catalogs = parse_catalogs(HTML)
    assert ("2", "50m Libre/50m Free") in catalogs["prueba"]
    assert ("6", "800m Libre/800m Free") in catalogs["prueba"]
    assert ("12 AÑOS", "12 AÑOS") in catalogs["categoria"]
    assert ("LC", "Larga") in catalogs["piscina"]


def test_select_ausente_no_aparece():
    catalogs = parse_catalogs(HTML)
    assert "liga" not in catalogs


JS = """
<script>
var opt_1 = new Array("25-29", "30-34");
var opt_2 = new Array("10 AÑOS", "11 AÑOS",
    "12 Y 13 Infantil B");
var opt_3 = new Array("10 AÑOS", "11 AÑOS", "12 Y 13 Infantil B");
</script>
"""


def test_parse_categorias_del_js():
    catalogs = parse_catalogs(HTML + JS)
    assert catalogs["categoria_master"] == [("25-29", "25-29"), ("30-34", "30-34")]
    assert ("12 Y 13 Infantil B", "12 Y 13 Infantil B") in catalogs["categoria_F"]
    assert len(catalogs["categoria_M"]) == 3
