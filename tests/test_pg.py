"""Traducción SQLite → PostgreSQL (sin necesitar un servidor Postgres)."""

from fecna_agent import db, pg


def test_placeholders_posicionales_y_nombrados():
    assert pg.translate_sql("SELECT * FROM t WHERE a = ? AND b = ?") == \
        "SELECT * FROM t WHERE a = %s AND b = %s"
    assert pg.translate_sql("VALUES (:x, :y)") == "VALUES (%(x)s, %(y)s)"


def test_insert_or_ignore():
    out = pg.translate_sql("INSERT OR IGNORE INTO catalogs (kind) VALUES (?)")
    assert out == "INSERT INTO catalogs (kind) VALUES (%s) ON CONFLICT DO NOTHING"


def test_porcentaje_literal_se_escapa_con_params():
    assert pg.translate_sql("SELECT '100%' WHERE a = ?") == "SELECT '100%%' WHERE a = %s"
    assert pg.translate_sql("SELECT '100%'", has_params=False) == "SELECT '100%'"


def test_casts_postgres_no_se_tocan():
    assert "::" in pg.translate_sql("SELECT a::int WHERE b = ?")


def test_esquema_pg():
    out = pg.translate_schema(db.SCHEMA)
    assert "AUTOINCREMENT" not in out and "SERIAL PRIMARY KEY" in out
    assert "TIMESTAMP" not in out and " DATE" not in out


def test_db_sin_sql_exclusivo_de_sqlite():
    import inspect
    src = inspect.getsource(db)
    assert "strftime" not in src


def test_row_por_nombre_e_indice():
    r = pg.Row(["a", "b"], [1, 2])
    assert r["a"] == 1 and r[1] == 2 and dict(r) == {"a": 1, "b": 2}


def test_toda_columna_migrada_se_verifica_al_arrancar():
    """Una columna en MIGRATIONS_SQL que no esté en la verificación nunca llega a una base existente
    (pasó con app_user.password_changed_at el 2026-11-23)."""
    import re

    from fecna_agent import db as dbm
    from fecna_agent import pg as pgm

    for table, column in re.findall(r"ALTER TABLE (\w+) ADD COLUMN IF NOT EXISTS (\w+)", pgm.MIGRATIONS_SQL):
        assert f"table_name = '{table}' AND column_name = '{column}'" in dbm._PG_READY_CHECK, (table, column)


def test_todo_indice_se_verifica_al_arrancar():
    """Un índice nuevo en SCHEMA que no esté en la verificación nunca se crea en una base existente."""
    import re

    from fecna_agent import db as dbm

    names = re.findall(r"CREATE INDEX IF NOT EXISTS (\w+)", dbm.SCHEMA)
    assert "idx_results_date" in names
    for name in names:
        assert f"to_regclass('public.{name}') IS NOT NULL" in dbm._PG_READY_CHECK, name
