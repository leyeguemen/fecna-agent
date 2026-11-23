"""Guarda para el SQL que escribe el LLM: un único SELECT sobre tablas públicas.

Lista blanca, no lista negra: la consulta se analiza con sqlglot y solo pasa si todas las tablas
que toca están en ALLOWED_TABLES (o son CTE visibles en ese punto) y todas las funciones están en
ALLOWED_FUNCTIONS. Se devuelve el SQL regenerado desde el árbol analizado, así lo que se ejecuta es
exactamente lo que se validó (sin diferencias entre cómo lo lee sqlglot y cómo lo lee la base).

En producción el chat consulta con el rol del backend (ignora RLS): esta guarda es la barrera.
"""

import logging

import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"ranking_public", "catalogs", "competition", "competition_entry", "sync_log"}
MAX_ROWS = 200

# Funciones de cálculo y texto que usa el chat. Todo lo demás (query_to_xml, set_config, pg_sleep,
# dblink, current_user, generate_series, lo_*, pg_*...) se rechaza.
ALLOWED_FUNCTIONS = {
    "COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND", "ABS", "FLOOR", "CEIL",
    "STDDEV", "STDDEV_POP", "STDDEV_SAMP", "VARIANCE",
    "COALESCE", "NULLIF", "GREATEST", "LEAST", "IF", "CASE", "AND", "OR",  # sqlglot trata estos operadores como funciones
    "LOWER", "UPPER", "LENGTH", "SUBSTRING", "TRIM", "REPLACE", "CONCAT", "STRING_AGG", "GROUP_CONCAT",
    "CAST", "TRY_CAST", "EXTRACT", "DATE", "DATE_TRUNC", "STRFTIME", "TO_CHAR",
    "CURRENT_DATE", "CURRENT_TIMESTAMP",
    "ROW_NUMBER", "RANK", "DENSE_RANK", "NTILE", "LAG", "LEAD", "FIRST_VALUE", "LAST_VALUE",
}

# Nodos que no caben en una lectura: escritura, DDL, SELECT INTO (crea tablas), FOR UPDATE, comandos.
_FORBIDDEN_NODES = tuple(t for t in (
    getattr(exp, n, None) for n in (
        "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "TruncateTable", "Command",
        "Into", "Lock", "Set", "Pragma", "Transaction", "Commit", "Rollback", "Copy", "Use", "Grant",
    )) if t is not None)

logging.getLogger("sqlglot").setLevel(logging.ERROR)  # sus avisos de sintaxis no van al log del servidor


def _parse(text: str, dialect: str) -> exp.Expression:
    try:
        statements = [s for s in sqlglot.parse(text, read=dialect) if s is not None]
    except sqlglot.errors.SqlglotError:
        raise ValueError("No se pudo interpretar la consulta.") from None
    if len(statements) != 1:
        raise ValueError("Solo se permite una sentencia.")
    return statements[0]


def _with_of(node: exp.Expression) -> exp.With | None:
    w = node.args.get("with_") or node.args.get("with")
    return w if isinstance(w, exp.With) else None


def _visible_cte(table: exp.Table) -> bool:
    """¿El nombre de la tabla es un CTE visible en ese punto?

    Dentro del cuerpo de un CTE solo se ven los CTE anteriores: «WITH app_user AS (SELECT * FROM
    app_user)» lee la tabla real, así que no cuenta como CTE.
    """
    name = table.name.lower()
    child, node, last_cte = table, table.parent, None
    while node is not None:
        if isinstance(node, exp.CTE):
            last_cte = node
        w = _with_of(node)
        if w is not None:
            ctes = list(w.expressions)
            visible = ctes[:ctes.index(last_cte)] if child is w and last_cte in ctes else ctes
            if name in {c.alias_or_name.lower() for c in visible}:
                return True
        child, node = node, node.parent
    return False


def _function_name(fn: exp.Func) -> str:
    return (fn.name if isinstance(fn, exp.Anonymous) else fn.sql_name()).upper()


def check_select(sql: str, dialect: str = "postgres") -> str:
    """Devuelve el SQL validado (regenerado) o lanza ValueError con el motivo.

    dialect: «postgres» (producción) o «sqlite» (local y pruebas).
    """
    text = (sql or "").strip().rstrip(";").strip()
    if not text:
        raise ValueError("Consulta vacía.")
    tree = _parse(text, dialect)
    if not isinstance(tree, exp.Query):
        raise ValueError("Solo se permite SELECT.")
    for node in tree.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            raise ValueError("Solo se permite leer: la consulta contiene una operación no permitida.")
        if isinstance(node, exp.With) and node.args.get("recursive"):
            raise ValueError("No se permiten consultas recursivas.")
        if isinstance(node, exp.Func) and _function_name(node) not in ALLOWED_FUNCTIONS:
            raise ValueError(f"Función no permitida: {_function_name(node).lower()}.")
    for table in tree.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier) or table.args.get("db") or table.args.get("catalog"):
            raise ValueError(f"Tabla no permitida. Usa: {', '.join(sorted(ALLOWED_TABLES))}.")
        if table.name.lower() not in ALLOWED_TABLES and not _visible_cte(table):
            raise ValueError(f"Tabla no permitida: {table.name}. Usa: {', '.join(sorted(ALLOWED_TABLES))}.")
    return tree.sql(dialect=dialect, comments=False)
