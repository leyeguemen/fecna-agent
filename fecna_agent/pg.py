"""Adaptador PostgreSQL (Supabase) con la misma interfaz que sqlite3 usa db.py.

db.py escribe SQL estilo SQLite (`?`, `:nombre`, `INSERT OR IGNORE`). Este módulo
lo traduce en el momento de ejecutar y devuelve filas con acceso por nombre e
índice (como sqlite3.Row), de modo que las funciones de db.py no cambian.

Las fechas se guardan como TEXT ISO (igual que en SQLite) para conservar el
comportamiento de comparaciones y formato.
"""

import re

PG_PREFIXES = ("postgres://", "postgresql://")


def is_pg_url(value) -> bool:
    return str(value).startswith(PG_PREFIXES)


# --------------------------------------------------------------- traducción

_PLACEHOLDER = re.compile(r"\?|(?<![:\w]):([A-Za-z_]\w*)")


def translate_sql(sql: str, has_params: bool = True) -> str:
    """SQLite → PostgreSQL para las construcciones que usa este proyecto."""
    out = sql.strip().rstrip(";")
    if re.match(r"(?is)^\s*INSERT\s+OR\s+IGNORE\s+INTO\b", out):
        out = re.sub(r"(?is)^\s*INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", out)
        out += " ON CONFLICT DO NOTHING"
    out = re.sub(r"\bLIKE\b", "ILIKE", out)  # SQLite LIKE ignora mayúsculas
    if has_params:
        out = out.replace("%", "%%")
        out = _PLACEHOLDER.sub(
            lambda m: f"%({m.group(1)})s" if m.group(1) else "%s", out
        )
    return out


TABLES = ("ranking_results", "catalogs", "sync_log", "competition",
          "competition_entry", "competition_watch", "app_user")

# Supabase expone las tablas por su API REST con la clave pública (anon). Con RLS
# activo y sin políticas, esa vía queda cerrada; el backend conecta con el rol
# postgres, que ignora RLS. Es obligatorio: hay datos personales de menores.
RLS_SQL = "".join(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;" for t in TABLES) + (
    # La vista respeta RLS del llamante: anon/authenticated (PostgREST) no ven nada.
    "ALTER VIEW ranking_public SET (security_invoker = true);"
)


def translate_schema(schema: str) -> str:
    """Esquema SQLite → PostgreSQL (fechas y timestamps como TEXT ISO)."""
    out = schema.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    out = out.replace("CREATE VIEW IF NOT EXISTS", "CREATE OR REPLACE VIEW")
    out = re.sub(r"\b(TIMESTAMP|DATE)\b", "TEXT", out)
    return out


# -------------------------------------------------------------------- filas

class Row:
    """Fila con acceso por nombre o posición, y keys(): reemplaza sqlite3.Row."""

    __slots__ = ("_names", "_values")

    def __init__(self, names, values):
        self._names = tuple(names)
        self._values = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return self._values[key]
        return self._values[self._names.index(key)]

    def keys(self):
        return list(self._names)

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __repr__(self):
        return f"Row({dict(zip(self._names, self._values))})"


def _row_factory(cursor):
    names = [c.name for c in (cursor.description or [])]

    def make(values):
        return Row(names, values)

    return make


# ---------------------------------------------------------------- conexión

class Cursor:
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return self._cur.rowcount

    def __iter__(self):
        return iter(self._cur)


class PgConnection:
    """Envuelve una conexión psycopg con la API mínima de sqlite3.Connection."""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params=None):
        cur = self._raw.cursor(row_factory=_row_factory)
        if params is None:
            cur.execute(translate_sql(sql, has_params=False))
        else:
            cur.execute(translate_sql(sql), params)
        return Cursor(cur)

    def executemany(self, sql: str, seq):
        cur = self._raw.cursor(row_factory=_row_factory)
        cur.executemany(translate_sql(sql), list(seq))
        return Cursor(cur)

    def executescript(self, script: str) -> None:
        # Ya viene en dialecto PostgreSQL (translate_schema): se ejecuta tal cual.
        self._raw.execute(script)
        self._raw.commit()

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()


def connect_pg(url: str) -> PgConnection:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "Falta 'psycopg'. Instala: pip install 'psycopg[binary]'"
        ) from exc
    # prepare_threshold=None: el pooler de Supabase (pgbouncer) no admite
    # sentencias preparadas.
    try:
        raw = psycopg.connect(
            url, autocommit=False, prepare_threshold=None, connect_timeout=15
        )
    except psycopg.OperationalError as exc:
        raise RuntimeError(
            "No se pudo conectar a Postgres. Si el host es db.<ref>.supabase.co, "
            "esa conexión directa es solo IPv6: usa la cadena del 'Session pooler' "
            "(aws-0-<región>.pooler.supabase.com, usuario postgres.<ref>).\n"
            f"Causa: {str(exc).strip()}"
        ) from None
    return PgConnection(raw)
