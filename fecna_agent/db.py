"""Almacenamiento y consultas exactas sobre SQLite.

Regla del proyecto: SQL/Python calcula, el LLM solo explica.
"""

import hashlib
import re
import sqlite3
from datetime import date
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "fecna.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ranking_results (
  source TEXT NOT NULL,
  ranking_position INTEGER,

  swimmer_id TEXT NOT NULL,
  swimmer_name TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,

  gender TEXT,
  birth_date DATE,
  birth_year_month TEXT,

  event_id TEXT NOT NULL,
  event_name TEXT NOT NULL,
  pool_type TEXT NOT NULL,

  time_raw TEXT NOT NULL,
  time_ms INTEGER NOT NULL,

  points INTEGER,
  result_date DATE,

  league TEXT,
  club TEXT,

  fetched_at TIMESTAMP,
  tournament TEXT,

  UNIQUE (swimmer_id, event_id, pool_type, time_ms, result_date)
);
CREATE INDEX IF NOT EXISTS idx_results_swimmer ON ranking_results (swimmer_id);
CREATE INDEX IF NOT EXISTS idx_results_event ON ranking_results (event_id, pool_type);
-- MAX(result_date) en GET /me ("Acerca de") y en el estado de sincronización: sin índice recorre la tabla.
CREATE INDEX IF NOT EXISTS idx_results_date ON ranking_results (result_date);

-- Vista sin datos sensibles (sin fecha de nacimiento exacta): es la única que ve el chat.
CREATE VIEW IF NOT EXISTS ranking_public AS
SELECT swimmer_id, swimmer_name, gender, SUBSTR(birth_date, 1, 4) AS birth_year,
       event_id, event_name, pool_type, time_raw, time_ms, points, result_date,
       league, club, tournament
FROM ranking_results;

CREATE TABLE IF NOT EXISTS catalogs (
  kind TEXT NOT NULL,
  code TEXT NOT NULL,
  label TEXT NOT NULL,
  UNIQUE (kind, code, label)
);

CREATE TABLE IF NOT EXISTS sync_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at TIMESTAMP NOT NULL,
  inicio DATE,
  fin DATE,
  combos INTEGER,
  received INTEGER,
  inserted INTEGER,
  errors INTEGER
);

CREATE TABLE IF NOT EXISTS competition (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  pool_type TEXT,
  source_format TEXT,
  content_hash TEXT,
  loaded_at TIMESTAMP,
  UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS competition_entry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competition_id INTEGER NOT NULL,
  event_number INTEGER,
  event_label TEXT,
  event_id TEXT,
  distance INTEGER,
  stroke TEXT,
  gender TEXT,
  category TEXT,
  session_no INTEGER,
  session_date DATE,
  heat INTEGER,
  lane INTEGER,
  start_time TEXT,
  swimmer_name TEXT NOT NULL,
  club_code TEXT,
  age INTEGER,
  seed_ms INTEGER,
  seed_raw TEXT,
  swimmer_id TEXT,
  FOREIGN KEY (competition_id) REFERENCES competition (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_entry_comp ON competition_entry (competition_id);

CREATE TABLE IF NOT EXISTS competition_watch (
  user_id INTEGER NOT NULL DEFAULT 0,
  competition_id INTEGER NOT NULL,
  swimmer_name TEXT NOT NULL,
  PRIMARY KEY (user_id, competition_id, swimmer_name),
  FOREIGN KEY (competition_id) REFERENCES competition (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_user (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  salt          TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'user',
  active        INTEGER NOT NULL DEFAULT 1,
  created_at    TIMESTAMP,
  swimmer_id    TEXT,
  terms_version TEXT,
  terms_accepted_at TIMESTAMP,
  password_changed_at INTEGER  -- epoch (s) del último cambio: los tokens emitidos antes dejan de valer
);

-- Marcas mínimas de los campeonatos nacionales (reglamento): una por torneo, año, categoría, género y prueba.
CREATE TABLE IF NOT EXISTS minimum_mark (
  tournament TEXT NOT NULL,
  year       INTEGER NOT NULL,
  category   TEXT NOT NULL,
  gender     TEXT NOT NULL,
  event_id   TEXT NOT NULL,
  time_ms    INTEGER NOT NULL,
  PRIMARY KEY (tournament, year, category, gender, event_id)
);

-- Historial completo de FECNA (Historial Deportivo) de nadadores seguidos/vinculados. Va aparte del
-- ranking para no alterar los puestos: ranking_results sigue siendo solo lo que publica el ranking.
CREATE TABLE IF NOT EXISTS swimmer_mark (
  swimmer_id  TEXT NOT NULL,
  event_id    TEXT NOT NULL,
  event_name  TEXT NOT NULL,
  pool_type   TEXT NOT NULL,
  time_ms     INTEGER NOT NULL,
  result_date DATE NOT NULL,
  points      INTEGER,
  tournament  TEXT,
  fetched_at  TIMESTAMP,
  UNIQUE (swimmer_id, event_id, pool_type, time_ms, result_date)
);

-- Roles y permisos (editables desde la app). Valores de partida: ver permisos.py
CREATE TABLE IF NOT EXISTS app_role (
  id        TEXT PRIMARY KEY,
  name      TEXT NOT NULL,
  is_system INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS app_permission (
  key       TEXT PRIMARY KEY,
  label     TEXT NOT NULL,
  is_system INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS role_permission (
  role_id        TEXT NOT NULL,
  permission_key TEXT NOT NULL,
  PRIMARY KEY (role_id, permission_key)
);

CREATE TABLE IF NOT EXISTS swimmer_follow (
  user_id      INTEGER NOT NULL,
  swimmer_id   TEXT NOT NULL,
  swimmer_name TEXT NOT NULL,
  PRIMARY KEY (user_id, swimmer_id)
);

-- Código vigente para recuperar la contraseña (uno por usuario; se borra al usarlo).
CREATE TABLE IF NOT EXISTS password_reset (
  user_id    INTEGER PRIMARY KEY,
  code_hash  TEXT NOT NULL,
  salt       TEXT NOT NULL,
  expires_at INTEGER NOT NULL,           -- epoch (s)
  attempts   INTEGER NOT NULL DEFAULT 0, -- intentos fallidos con este código
  sent_at    INTEGER NOT NULL            -- epoch (s) del envío: limita los reenvíos
);
"""

ENTRY_COLUMNS = [
    "event_number", "event_label", "event_id", "distance", "stroke", "gender",
    "category", "session_no", "session_date", "heat", "lane", "start_time",
    "swimmer_name", "club_code", "age", "seed_ms", "seed_raw", "swimmer_id",
]

COLUMNS = [
    "source", "ranking_position", "swimmer_id", "swimmer_name", "first_name",
    "last_name", "gender", "birth_date", "birth_year_month", "event_id",
    "event_name", "pool_type", "time_raw", "time_ms", "points", "result_date",
    "league", "club", "fetched_at",
]


_PG_SCHEMA_READY: set[str] = set()  # URLs cuyo esquema ya se verificó en este proceso
_PG_MIGRATION_LOCK = 4270001  # clave de pg_advisory_lock: un solo migrador a la vez
# Si algo de esto falta, se corre la migración. Toda columna nueva de pg.MIGRATIONS_SQL y todo índice
# de SCHEMA deben estar aquí (lo verifica tests/test_pg.py): si no, una base existente nunca la recibe.
_PG_READY_CHECK = """SELECT to_regclass('public.swimmer_follow') IS NOT NULL
                   AND to_regclass('public.ranking_public') IS NOT NULL
                   AND EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name = 'app_user' AND column_name = 'swimmer_id')
                   AND EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name = 'app_user' AND column_name = 'terms_version')
                   AND EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name = 'app_user' AND column_name = 'terms_accepted_at')
                   AND EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name = 'app_user' AND column_name = 'password_changed_at')
                   AND EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name = 'ranking_results' AND column_name = 'tournament')
                   AND to_regclass('public.app_role') IS NOT NULL
                   AND to_regclass('public.swimmer_mark') IS NOT NULL
                   AND to_regclass('public.minimum_mark') IS NOT NULL
                   AND to_regclass('public.password_reset') IS NOT NULL
                   AND to_regclass('public.idx_results_swimmer') IS NOT NULL
                   AND to_regclass('public.idx_results_event') IS NOT NULL
                   AND to_regclass('public.idx_results_date') IS NOT NULL
                   AND to_regclass('public.idx_entry_comp') IS NOT NULL"""


def _ensure_pg_schema(conn, url: str) -> None:
    """Crea/actualiza el esquema de Postgres solo cuando hace falta.

    Antes se ejecutaba el DDL en CADA conexión (cada petición de la API): tomaba bloqueos
    exclusivos sobre las tablas y provocó un deadlock con una sincronización en curso. Ahora
    se verifica con consultas de catálogo (sin bloquear tablas), el DDL corre bajo un
    advisory lock y solo si falta algo, y el resultado se recuerda por proceso.
    """
    from . import pg

    if url in _PG_SCHEMA_READY:
        return
    check = _PG_READY_CHECK
    ready = conn.execute(check).fetchone()[0]
    conn.commit()  # suelta cualquier bloqueo de la consulta de verificación
    if not ready:
        conn.execute(f"SELECT pg_advisory_lock({_PG_MIGRATION_LOCK})")
        try:
            if not conn.execute(check).fetchone()[0]:  # otro proceso pudo migrar mientras esperábamos
                conn.commit()
                conn.executescript(pg.PRE_MIGRATIONS_SQL)
                conn.executescript(pg.translate_schema(SCHEMA))
                conn.executescript(pg.RLS_SQL)
                conn.executescript(pg.MIGRATIONS_SQL)
                seed_roles(conn)
                seed_minimums(conn)
            conn.commit()
        finally:
            conn.execute(f"SELECT pg_advisory_unlock({_PG_MIGRATION_LOCK})")
            conn.commit()
    # Una vez por proceso: si el código trae permisos de sistema nuevos, se registran (y el admin los recibe).
    seed_roles(conn)
    seed_minimums(conn)
    _PG_SCHEMA_READY.add(url)


def connect(db_path: Path | str = DEFAULT_DB_PATH):
    """SQLite local (ruta) o PostgreSQL/Supabase (URL postgresql://...)."""
    from . import pg

    if pg.is_pg_url(db_path):
        conn = pg.connect_pg(str(db_path))
        _ensure_pg_schema(conn, str(db_path))
        return conn
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    seed_roles(conn)
    seed_minimums(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Migraciones suaves para bases creadas con un esquema anterior."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(competition)")}
    if "content_hash" not in cols:
        conn.execute("ALTER TABLE competition ADD COLUMN content_hash TEXT")
        conn.commit()

    rr_cols = {r["name"] for r in conn.execute("PRAGMA table_info(ranking_results)")}
    if rr_cols and "tournament" not in rr_cols:
        conn.execute("ALTER TABLE ranking_results ADD COLUMN tournament TEXT")
        conn.execute("DROP VIEW IF EXISTS ranking_public")  # se recrea con la columna nueva
        conn.executescript(SCHEMA)
        conn.commit()

    user_cols = {r["name"] for r in conn.execute("PRAGMA table_info(app_user)")}
    if user_cols and "swimmer_id" not in user_cols:
        conn.execute("ALTER TABLE app_user ADD COLUMN swimmer_id TEXT")
        conn.commit()
    if user_cols and "terms_version" not in user_cols:
        conn.execute("ALTER TABLE app_user ADD COLUMN terms_version TEXT")
        conn.execute("ALTER TABLE app_user ADD COLUMN terms_accepted_at TIMESTAMP")
        conn.commit()
    if user_cols and "password_changed_at" not in user_cols:
        conn.execute("ALTER TABLE app_user ADD COLUMN password_changed_at INTEGER")
        conn.commit()

    watch_cols = {r["name"] for r in conn.execute("PRAGMA table_info(competition_watch)")}
    if watch_cols and "user_id" not in watch_cols:
        conn.execute("ALTER TABLE competition_watch RENAME TO competition_watch_old")
        conn.execute(
            """CREATE TABLE competition_watch (
                 user_id INTEGER NOT NULL DEFAULT 0,
                 competition_id INTEGER NOT NULL,
                 swimmer_name TEXT NOT NULL,
                 PRIMARY KEY (user_id, competition_id, swimmer_name),
                 FOREIGN KEY (competition_id) REFERENCES competition (id) ON DELETE CASCADE
               )"""
        )
        conn.execute(
            """INSERT OR IGNORE INTO competition_watch
               (user_id, competition_id, swimmer_name)
               SELECT 0, competition_id, swimmer_name FROM competition_watch_old"""
        )
        conn.execute("DROP TABLE competition_watch_old")
        conn.commit()


def insert_results(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Inserta resultados; los duplicados (UNIQUE) se ignoran. Devuelve cuántos
    registros nuevos se insertaron."""
    placeholders = ", ".join(f":{col}" for col in COLUMNS)
    sql = f"INSERT OR IGNORE INTO ranking_results ({', '.join(COLUMNS)}) VALUES ({placeholders})"
    before = conn.execute("SELECT COUNT(*) FROM ranking_results").fetchone()[0]
    conn.executemany(sql, rows)
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM ranking_results").fetchone()[0]
    return after - before


def save_catalogs(conn: sqlite3.Connection, catalogs: dict[str, list[tuple[str, str]]]) -> int:
    """Guarda los catálogos (pruebas, categorías, ...) reemplazando cada kind."""
    total = 0
    for kind, entries in catalogs.items():
        conn.execute("DELETE FROM catalogs WHERE kind = ?", (kind,))
        conn.executemany(
            "INSERT OR IGNORE INTO catalogs (kind, code, label) VALUES (?, ?, ?)",
            [(kind, code, label) for code, label in entries],
        )
        total += len(entries)
    conn.commit()
    return total


def get_catalog(conn: sqlite3.Connection, kind: str) -> list[tuple[str, str]]:
    rows = conn.execute(
        "SELECT code, label FROM catalogs WHERE kind = ? ORDER BY label", (kind,)
    ).fetchall()
    return [(row["code"], row["label"]) for row in rows]


def list_events(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Pruebas con datos en la base (a diferencia del catálogo completo)."""
    rows = conn.execute(
        "SELECT DISTINCT event_id, event_name FROM ranking_results ORDER BY event_name"
    ).fetchall()
    return [(row["event_id"], row["event_name"]) for row in rows]


def list_leagues(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """SELECT DISTINCT league FROM ranking_results
           WHERE league IS NOT NULL AND league != '' ORDER BY league"""
    ).fetchall()
    return [row["league"] for row in rows]


def list_swimmers(
    conn: sqlite3.Connection,
    league: str | None = None,
    age_range: tuple[int, int] | None = None,
    reference_year: int | None = None,
) -> list[tuple[str, str]]:
    """Nadadores únicos en la base (para el índice semántico y los selectores).

    league filtra por tener al menos un resultado en esa liga. age_range
    filtra por categoría FECNA: año de referencia (defecto: el actual) −
    año de nacimiento."""
    where, params = "", []
    if league:
        where += " AND league = ?"
        params.append(league)
    if age_range:
        where += (" AND birth_date IS NOT NULL AND "
                  "? - CAST(SUBSTR(birth_date, 1, 4) AS INTEGER) BETWEEN ? AND ?")
        params.extend([reference_year or date.today().year, *age_range])
    rows = conn.execute(
        f"""SELECT DISTINCT swimmer_id, swimmer_name FROM ranking_results
            WHERE 1=1 {where} ORDER BY swimmer_name""",
        params,
    ).fetchall()
    return [(row["swimmer_id"], row["swimmer_name"]) for row in rows]


def list_swimmers_detailed(
    conn: sqlite3.Connection,
    league: str | None = None,
    age_range: tuple[int, int] | None = None,
    reference_year: int | None = None,
) -> list[tuple[str, str, str | None, str | None]]:
    """Como list_swimmers pero añade club y liga (los más recientes de cada
    nadador) para identificarlo sin mostrar la cédula en los selectores."""
    swimmers = list_swimmers(conn, league, age_range, reference_year)
    if not swimmers:
        return []
    ids = [sid for sid, _ in swimmers]
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"""SELECT swimmer_id, club, league FROM (
              SELECT swimmer_id, club, league,
                     ROW_NUMBER() OVER (PARTITION BY swimmer_id
                         ORDER BY result_date DESC, fetched_at DESC) AS rn
              FROM ranking_results WHERE swimmer_id IN ({placeholders})
            ) t WHERE rn = 1""",
        ids,
    ).fetchall()
    affiliation = {r["swimmer_id"]: (r["club"], r["league"]) for r in rows}
    return [(sid, name, *affiliation.get(sid, (None, None))) for sid, name in swimmers]


def pseudonym(swimmer_id: str) -> str:
    """Código estable y no reversible que reemplaza la identificación real."""
    return "A" + hashlib.sha1(str(swimmer_id).encode()).hexdigest()[:9].upper()


def export_anonymized(conn: sqlite3.Connection, dest_path: Path | str) -> int:
    """Escribe una copia anonimizada de la base apta para publicar.

    - La identificación se reemplaza por un pseudónimo estable (se preservan los
      cruces y rankings, pero no la cédula real).
    - La fecha de nacimiento se reduce al año (suficiente para la categoría, sin
      exponer la fecha exacta).
    Nombres, clubes, ligas y tiempos se conservan (son datos públicos del sitio).
    """
    dest = connect(dest_path)
    dest.execute("DELETE FROM ranking_results")
    dest.execute("DELETE FROM catalogs")

    anon = []
    for row in conn.execute("SELECT * FROM ranking_results"):
        record = dict(row)
        record["swimmer_id"] = pseudonym(record["swimmer_id"])
        if record.get("birth_date"):
            record["birth_date"] = f"{str(record['birth_date'])[:4]}-01-01"
        anon.append(record)
    inserted = insert_results(dest, anon)

    catalogs = conn.execute("SELECT kind, code, label FROM catalogs").fetchall()
    dest.executemany(
        "INSERT OR IGNORE INTO catalogs (kind, code, label) VALUES (?, ?, ?)",
        [(c["kind"], c["code"], c["label"]) for c in catalogs],
    )
    dest.commit()
    dest.close()
    return inserted


def log_sync(conn: sqlite3.Connection, stats: dict) -> None:
    conn.execute(
        """INSERT INTO sync_log (run_at, inicio, fin, combos, received, inserted, errors)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (stats["run_at"], stats["inicio"], stats["fin"], stats["combos"],
         stats["received"], stats["inserted"], stats["errors"]),
    )
    conn.commit()


def last_sync(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()


def results_from_run(conn: sqlite3.Connection, run_at: str) -> list[sqlite3.Row]:
    """Resultados que entraron nuevos en una corrida de sincronización."""
    return conn.execute(
        """SELECT * FROM ranking_results WHERE fetched_at = ?
           ORDER BY event_name, pool_type, time_ms""",
        (run_at,),
    ).fetchall()


def summarize_run(conn: sqlite3.Connection, run_at: str) -> list[sqlite3.Row]:
    """Novedades de una corrida agrupadas por prueba/piscina/género."""
    return conn.execute(
        """SELECT event_name, pool_type, gender, COUNT(*) AS nuevos
           FROM ranking_results WHERE fetched_at = ?
           GROUP BY event_name, pool_type, gender
           ORDER BY event_name, pool_type, gender""",
        (run_at,),
    ).fetchall()


def _filters(
    event_id: str | None,
    pool_type: str | None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[str, list]:
    clauses, params = [], []
    if event_id:
        clauses.append("AND event_id = ?")
        params.append(event_id)
    if pool_type:
        clauses.append("AND pool_type = ?")
        params.append(pool_type)
    if date_from:
        clauses.append("AND result_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("AND result_date <= ?")
        params.append(date_to)
    return " ".join(clauses), params


def best_time(
    conn: sqlite3.Connection,
    swimmer_id: str,
    event_id: str | None = None,
    pool_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> sqlite3.Row | None:
    """Mejor marca (menor time_ms) de un nadador."""
    where, params = _filters(event_id, pool_type, date_from, date_to)
    return conn.execute(
        f"""SELECT * FROM ranking_results
            WHERE swimmer_id = ? {where}
            ORDER BY time_ms ASC LIMIT 1""",
        [swimmer_id, *params],
    ).fetchone()


def compare_swimmers(
    conn: sqlite3.Connection,
    swimmer_a: str,
    swimmer_b: str,
    event_id: str,
    pool_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Compara las mejores marcas de dos nadadores en una prueba.

    Devuelve {'a': Row|None, 'b': Row|None, 'diff_ms': int|None}.
    """
    a = best_time(conn, swimmer_a, event_id, pool_type, date_from, date_to)
    b = best_time(conn, swimmer_b, event_id, pool_type, date_from, date_to)
    diff_ms = abs(a["time_ms"] - b["time_ms"]) if a and b else None
    return {"a": a, "b": b, "diff_ms": diff_ms}


def ranking(
    conn: sqlite3.Connection,
    event_id: str,
    pool_type: str | None = None,
    gender: str | None = None,
    limit: int = 20,
    league: str | None = None,
    age_range: tuple[int, int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[sqlite3.Row]:
    """Ranking por mejor marca de cada nadador en una prueba.

    age_range filtra por categoría FECNA: año de referencia − año de
    nacimiento. El año de referencia es el de date_to (o el actual si no
    se acotan fechas); no depende de la fecha de cada resultado.
    date_from/date_to (ISO) acotan la fecha del resultado: útil para el
    ranking de un campeonato o una temporada."""
    where, params = _filters(event_id, pool_type, date_from, date_to)
    if gender:
        where += " AND gender = ?"
        params.append(gender)
    if league:
        where += " AND league = ?"
        params.append(league)
    if age_range:
        reference_year = int(date_to[:4]) if date_to else date.today().year
        where += (" AND birth_date IS NOT NULL AND "
                  "? - CAST(SUBSTR(birth_date, 1, 4) AS INTEGER) BETWEEN ? AND ?")
        params.extend([reference_year, *age_range])
    return conn.execute(
        f"""SELECT swimmer_id, swimmer_name, gender, birth_date, club, league,
                   time_ms, time_raw, result_date
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                           PARTITION BY swimmer_id
                           ORDER BY time_ms ASC, result_date DESC) AS rn
                FROM ranking_results
                WHERE 1=1 {where}
            ) t
            WHERE rn = 1
            ORDER BY time_ms ASC LIMIT ?""",
        [*params, limit],
    ).fetchall()


def history(
    conn: sqlite3.Connection,
    swimmer_id: str,
    event_id: str | None = None,
    pool_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[sqlite3.Row]:
    """Evolución de marcas de un nadador ordenada por fecha."""
    where, params = _filters(event_id, pool_type, date_from, date_to)
    return conn.execute(
        f"""SELECT * FROM ranking_results
            WHERE swimmer_id = ? {where}
            ORDER BY result_date ASC, time_ms ASC""",
        [swimmer_id, *params],
    ).fetchall()


def swimmer_event_ranks(
    conn: sqlite3.Connection,
    swimmer_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[sqlite3.Row]:
    """Para cada prueba/piscina que el nadador ha nadado, su mejor marca y su
    puesto en el ranking, por género y categoría: a nivel de su liga y nacional.

    El ranking se calcula por género (convención en natación) y dentro de la
    categoría del nadador (edad = año de referencia − año de nacimiento, como
    asigna FECNA). El año de referencia es el de date_to, o el actual. La liga
    del nadador es la más reciente que ha representado, y el puesto de liga lo
    compara contra quienes pertenecen a esa misma liga y categoría."""
    date_where, date_params = _filters(None, None, date_from, date_to)
    reference_year = int(date_to[:4]) if date_to else date.today().year
    return conn.execute(
        f"""
        WITH filtered AS (
            SELECT * FROM ranking_results WHERE 1=1 {date_where}
        ),
        swimmer_league AS (
            SELECT swimmer_id, league FROM (
                SELECT swimmer_id, league,
                       ROW_NUMBER() OVER (
                           PARTITION BY swimmer_id
                           ORDER BY result_date DESC, fetched_at DESC
                       ) AS rn
                FROM filtered
                WHERE league IS NOT NULL AND league != ''
            ) t WHERE rn = 1
        ),
        swimmer_club AS (
            SELECT swimmer_id, club FROM (
                SELECT swimmer_id, club,
                       ROW_NUMBER() OVER (
                           PARTITION BY swimmer_id
                           ORDER BY result_date DESC, fetched_at DESC
                       ) AS rn
                FROM filtered
                WHERE club IS NOT NULL AND club != ''
            ) t WHERE rn = 1
        ),
        best AS (
            SELECT f.swimmer_id, MIN(f.swimmer_name) AS swimmer_name, f.event_id,
                   MIN(f.event_name) AS event_name, f.pool_type,
                   MIN(f.gender) AS gender, MIN(sl.league) AS league,
                   MIN(sc.club) AS club,
                   ? - CAST(SUBSTR(MIN(f.birth_date), 1, 4) AS INTEGER) AS age,
                   MIN(f.time_ms) AS best_ms
            FROM filtered f
            LEFT JOIN swimmer_league sl ON sl.swimmer_id = f.swimmer_id
            LEFT JOIN swimmer_club sc ON sc.swimmer_id = f.swimmer_id
            WHERE f.birth_date IS NOT NULL
            GROUP BY f.swimmer_id, f.event_id, f.pool_type
        ),
        ranked AS (
            SELECT *,
                RANK() OVER (PARTITION BY event_id, pool_type, gender, age
                             ORDER BY best_ms) AS national_rank,
                COUNT(*) OVER (PARTITION BY event_id, pool_type, gender, age)
                             AS national_total,
                RANK() OVER (PARTITION BY event_id, pool_type, gender, age, league
                             ORDER BY best_ms) AS league_rank,
                COUNT(*) OVER (PARTITION BY event_id, pool_type, gender, age, league)
                             AS league_total
            FROM best
        )
        SELECT swimmer_name, event_id, event_name, pool_type, gender, league, club,
               age, best_ms, national_rank, national_total, league_rank, league_total
        FROM ranked
        WHERE swimmer_id = ?
        ORDER BY event_name, pool_type
        """,
        [*date_params, reference_year, swimmer_id],
    ).fetchall()


def event_index(conn: sqlite3.Connection) -> list[tuple[str, int, str]]:
    """(event_id, distancia, estilo_canónico) para mapear las pruebas del PDF.

    Se construye desde el catálogo de pruebas (o, en su defecto, de los eventos
    presentes en la base). El estilo se deduce del nombre con programa.stroke_key."""
    from . import programa

    rows = get_catalog(conn, "prueba") or list_events(conn)
    index = []
    for _code, label in rows:
        dist = next((int(m) for m in re.findall(r"(\d+)\s*m", label.lower())), None)
        event_id = next(
            (eid for eid, name in list_events(conn) if name == label), _code
        )
        stroke = programa.stroke_key(label)
        if dist and stroke:
            index.append((event_id, dist, stroke))
    return index


def save_competition(
    conn: sqlite3.Connection, competition: dict, entries: list[dict]
) -> dict:
    """Guarda un programa de campeonato y sus inscripciones.

    Si ya existe un campeonato con el mismo nombre y la programación NO cambió
    (misma huella de contenido), no hace nada. Solo reescribe cuando hay cambios.

    Devuelve {'competition_id': int, 'status': 'created'|'updated'|'unchanged'}.
    """
    from datetime import datetime

    from . import programa

    name = competition.get("name") or "Campeonato sin título"
    new_hash = programa.fingerprint(competition, entries)
    existing = conn.execute(
        "SELECT id, content_hash FROM competition WHERE name = ?", (name,)
    ).fetchone()

    if existing and existing["content_hash"] == new_hash:
        return {"competition_id": existing["id"], "status": "unchanged"}

    status = "updated" if existing else "created"
    conn.execute(
        """INSERT INTO competition (name, pool_type, source_format, content_hash, loaded_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
             pool_type=excluded.pool_type, source_format=excluded.source_format,
             content_hash=excluded.content_hash, loaded_at=excluded.loaded_at""",
        (name, competition.get("pool_type"), competition.get("source_format"),
         new_hash, datetime.now().isoformat(timespec="seconds")),
    )
    comp_id = conn.execute(
        "SELECT id FROM competition WHERE name = ?", (name,)
    ).fetchone()[0]
    conn.execute("DELETE FROM competition_entry WHERE competition_id = ?", (comp_id,))
    placeholders = ", ".join(f":{c}" for c in ENTRY_COLUMNS)
    conn.executemany(
        f"""INSERT INTO competition_entry (competition_id, {', '.join(ENTRY_COLUMNS)})
            VALUES ({comp_id}, {placeholders})""",
        entries,
    )
    conn.commit()
    return {"competition_id": comp_id, "status": status}


def list_competitions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT c.id, c.name, c.pool_type, c.loaded_at,
                  COUNT(e.id) AS entradas
           FROM competition c LEFT JOIN competition_entry e
                ON e.competition_id = c.id
           GROUP BY c.id ORDER BY c.loaded_at DESC"""
    ).fetchall()


def delete_competition(conn: sqlite3.Connection, comp_id: int) -> None:
    conn.execute("DELETE FROM competition_watch WHERE competition_id = ?", (comp_id,))
    conn.execute("DELETE FROM competition_entry WHERE competition_id = ?", (comp_id,))
    conn.execute("DELETE FROM competition WHERE id = ?", (comp_id,))
    conn.commit()


def competition_clubs(conn: sqlite3.Connection, comp_id: int) -> list[str]:
    rows = conn.execute(
        """SELECT DISTINCT club_code FROM competition_entry
           WHERE competition_id = ? AND club_code IS NOT NULL
           ORDER BY club_code""",
        (comp_id,),
    ).fetchall()
    return [r["club_code"] for r in rows]


def competition_swimmers(conn: sqlite3.Connection, comp_id: int) -> list[tuple[str, str]]:
    """(nombre, club_code) distintos del programa, para el selector de nadador."""
    rows = conn.execute(
        """SELECT DISTINCT swimmer_name, club_code FROM competition_entry
           WHERE competition_id = ? ORDER BY swimmer_name""",
        (comp_id,),
    ).fetchall()
    return [(r["swimmer_name"], r["club_code"]) for r in rows]


def competition_schedule(
    conn: sqlite3.Connection,
    comp_id: int,
    club_code: str | None = None,
    swimmer_name: str | None = None,
) -> list[sqlite3.Row]:
    """Cronograma del campeonato, ordenado por jornada y hora de inicio."""
    where, params = "", [comp_id]
    if club_code:
        where += " AND club_code = ?"
        params.append(club_code)
    rows = conn.execute(
        f"""SELECT * FROM competition_entry
            WHERE competition_id = ? {where}
            ORDER BY session_date IS NULL, session_date,
                     start_time IS NULL, start_time, event_number, heat, lane""",
        params,
    ).fetchall()
    if swimmer_name:
        # Búsqueda por palabras, sin importar mayúsculas ni tildes: «samuel g» encuentra
        # «Samuel Guerrero Blandon». Cada palabra buscada debe iniciar alguna palabra del nombre.
        from .programa import normalize_name

        terms = normalize_name(swimmer_name).split()
        rows = [r for r in rows
                if all(any(w.startswith(t) for w in normalize_name(r["swimmer_name"]).split()) for t in terms)]
    return rows


def list_watched(conn: sqlite3.Connection, comp_id: int, user_id: int = 0) -> list[str]:
    """Nombres de nadadores seguidos por un usuario en un campeonato."""
    rows = conn.execute(
        "SELECT swimmer_name FROM competition_watch WHERE competition_id = ? AND user_id = ? "
        "ORDER BY swimmer_name",
        (comp_id, user_id),
    ).fetchall()
    return [r["swimmer_name"] for r in rows]


def set_watched(
    conn: sqlite3.Connection,
    comp_id: int,
    swimmer_names: list[str],
    user_id: int = 0,
) -> None:
    """Reemplaza los nadadores seguidos por un usuario en un campeonato."""
    conn.execute(
        "DELETE FROM competition_watch WHERE competition_id = ? AND user_id = ?",
        (comp_id, user_id),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO competition_watch (user_id, competition_id, swimmer_name) "
        "VALUES (?, ?, ?)",
        [(user_id, comp_id, n) for n in swimmer_names],
    )
    conn.commit()


def watched_schedule(
    conn: sqlite3.Connection, comp_id: int, user_id: int = 0
) -> list[sqlite3.Row]:
    """Cronograma de inscripciones de los nadadores seguidos por un usuario."""
    # Incluye los nadadores vigilados en este campeonato y los que el usuario sigue
    # (o su propio nadador): coincidencia por id o por nombre.
    return conn.execute(
        """SELECT e.* FROM competition_entry e
           WHERE e.competition_id = ?
             AND (EXISTS (SELECT 1 FROM competition_watch w
                          WHERE w.competition_id = e.competition_id
                            AND w.swimmer_name = e.swimmer_name AND w.user_id = ?)
                  OR EXISTS (SELECT 1 FROM swimmer_follow f
                             WHERE f.user_id = ? AND (f.swimmer_id = e.swimmer_id
                                   OR LOWER(f.swimmer_name) = LOWER(e.swimmer_name))))
           ORDER BY session_date IS NULL, session_date,
                    start_time IS NULL, start_time, event_number, heat, lane""",
        (comp_id, user_id, user_id),
    ).fetchall()


def upcoming_entries(
    conn: sqlite3.Connection, user_id: int, swimmer_id: str | None, today: str
) -> list[sqlite3.Row]:
    """Próximas inscripciones (desde `today`, AAAA-MM-DD) del nadador vinculado, de los que el
    usuario sigue y de los que vigila en cada campeonato, con el nombre del campeonato."""
    own, params = "", [today]
    if swimmer_id:
        own = "e.swimmer_id = ? OR "
        params.append(swimmer_id)
    return conn.execute(
        f"""SELECT e.*, c.name AS competition_name FROM competition_entry e
           JOIN competition c ON c.id = e.competition_id
           WHERE e.session_date >= ?
             AND ({own}EXISTS (SELECT 1 FROM competition_watch w
                             WHERE w.competition_id = e.competition_id
                               AND w.swimmer_name = e.swimmer_name AND w.user_id = ?)
                  OR EXISTS (SELECT 1 FROM swimmer_follow f
                             WHERE f.user_id = ? AND (f.swimmer_id = e.swimmer_id
                                   OR LOWER(f.swimmer_name) = LOWER(e.swimmer_name))))
           ORDER BY e.session_date, e.start_time IS NULL, e.start_time, e.event_number, e.heat, e.lane""",
        (*params, user_id, user_id),
    ).fetchall()


def watched_entry(
    conn: sqlite3.Connection, entry_id: int, user_id: int = 0
) -> sqlite3.Row | None:
    """Detalle de una inscripción seguida por el usuario."""
    return conn.execute(
        """SELECT e.*, c.name AS competition_name, c.pool_type AS competition_pool
           FROM competition_entry e
           JOIN competition c ON c.id = e.competition_id
           JOIN competition_watch w
             ON w.competition_id = e.competition_id AND w.swimmer_name = e.swimmer_name
           WHERE e.id = ? AND w.user_id = ?""",
        (entry_id, user_id),
    ).fetchone()


def create_user(
    conn: sqlite3.Connection, email: str, password: str, role: str = "user",
    terms_version: str | None = None,
) -> dict:
    """Crea un usuario (valida email/contraseña/unicidad). Devuelve el registro.

    Lanza ValueError con mensaje en español si algo no cumple."""
    from datetime import datetime

    from . import auth

    email = auth.normalize_email(email)
    if not auth.valid_email(email):
        raise ValueError("Email inválido.")
    err = auth.valid_password(password)
    if err:
        raise ValueError(err)
    if get_user_by_email(conn, email) is not None:
        raise ValueError("Ese email ya está registrado.")
    hash_hex, salt_hex = auth.hash_password(password)
    conn.execute(
        """INSERT INTO app_user (email, password_hash, salt, role, active, created_at,
                                 terms_version, terms_accepted_at)
           VALUES (?, ?, ?, ?, 1, ?, ?, ?)""",
        (email, hash_hex, salt_hex, role,
         datetime.now().isoformat(timespec="seconds"),
         terms_version, datetime.now().isoformat(timespec="seconds") if terms_version else None),
    )
    conn.commit()
    return dict(get_user_by_email(conn, email))


def get_user_by_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    from . import auth
    return conn.execute(
        "SELECT * FROM app_user WHERE email = ?", (auth.normalize_email(email),)
    ).fetchone()


def check_login(conn: sqlite3.Connection, email: str, password: str) -> tuple[sqlite3.Row | None, str]:
    """(usuario, estado): «ok», «inactive» (clave correcta pero cuenta desactivada) o «invalid».

    «inactive» solo sale con la clave correcta: a quien no la sabe no se le revela si la cuenta
    existe. Siempre se calcula un PBKDF2 (verificar o hash de descarte), así el tiempo de
    respuesta tampoco revela qué emails existen."""
    from . import auth
    row = get_user_by_email(conn, email)
    if row is None:
        auth.hash_password(password)  # gasta el mismo costo de PBKDF2 que el camino normal
        return None, "invalid"
    if not auth.verify_password(password, row["password_hash"], row["salt"]):
        return None, "invalid"
    return (row, "ok") if row["active"] else (None, "inactive")


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> sqlite3.Row | None:
    """Devuelve el Row del usuario si las credenciales son válidas y está activo."""
    return check_login(conn, email, password)[0]


# --- Roles y permisos ---------------------------------------------------------------

def seed_roles(conn) -> None:
    """Siembra permisos de sistema y roles de partida; no pisa lo que el admin ya cambió."""
    from . import permisos

    for key, label in permisos.SYSTEM_PERMISSIONS.items():
        conn.execute("INSERT OR IGNORE INTO app_permission (key, label, is_system) VALUES (?, ?, 1)", (key, label))
    for rid, (name, perms) in permisos.DEFAULT_ROLES.items():
        known = conn.execute("SELECT 1 FROM app_role WHERE id = ?", (rid,)).fetchone()
        if not known:
            conn.execute("INSERT OR IGNORE INTO app_role (id, name, is_system) VALUES (?, ?, 1)", (rid, name))
            for key in perms:
                conn.execute("INSERT OR IGNORE INTO role_permission (role_id, permission_key) VALUES (?, ?)", (rid, key))
    # El admin conserva siempre todos los permisos, incluidos los que se agreguen después.
    conn.execute(
        "INSERT OR IGNORE INTO role_permission (role_id, permission_key) "
        "SELECT ?, key FROM app_permission", (permisos.ADMIN_ROLE,))
    conn.commit()


def seed_minimums(conn) -> None:
    """Carga las marcas del reglamento 2026 solo si la tabla está vacía (no pisa lo que el admin corrija)."""
    from . import minimas

    if conn.execute("SELECT 1 FROM minimum_mark LIMIT 1").fetchone():
        return
    for tournament, category, gender, event_id, ms in minimas.reglamento_2026():
        conn.execute("INSERT OR IGNORE INTO minimum_mark (tournament, year, category, gender, event_id, time_ms) "
                     "VALUES (?, ?, ?, ?, ?, ?)", (tournament, minimas.YEAR, category, gender, event_id, ms))
    conn.commit()


def minimum_marks(conn, tournament: str, category: str, gender: str, year: int | None = None) -> dict[str, int]:
    """event_id → marca mínima (ms) de esa categoría; del año más reciente si no se indica."""
    if year is None:
        row = conn.execute("SELECT MAX(year) FROM minimum_mark WHERE tournament = ?", (tournament,)).fetchone()
        year = row[0]
    if year is None:
        return {}
    rows = conn.execute("SELECT event_id, time_ms FROM minimum_mark WHERE tournament = ? AND year = ? "
                        "AND category = ? AND gender = ?", (tournament, year, category, gender)).fetchall()
    return {r[0]: r[1] for r in rows}


def minimum_years(conn) -> dict[str, int]:
    """Torneo → año vigente (el más reciente cargado)."""
    rows = conn.execute("SELECT tournament, MAX(year) FROM minimum_mark GROUP BY tournament").fetchall()
    return {r[0]: r[1] for r in rows}


def save_minimum_marks(conn, tournament: str, year: int, category: str, gender: str, marks: dict[str, int]) -> int:
    """Reemplaza las marcas de una categoría/género. marks: event_id → ms (las ausentes se borran)."""
    conn.execute("DELETE FROM minimum_mark WHERE tournament = ? AND year = ? AND category = ? AND gender = ?",
                 (tournament, year, category, gender))
    for event_id, ms in marks.items():
        conn.execute("INSERT INTO minimum_mark (tournament, year, category, gender, event_id, time_ms) "
                     "VALUES (?, ?, ?, ?, ?, ?)", (tournament, year, category, gender, event_id, ms))
    conn.commit()
    return len(marks)


def swimmer_bests(conn, swimmer_id: str, pool_type: str = "LC") -> dict[str, int]:
    """Mejor marca por prueba (event_id → ms) en esa piscina, con el historial completo."""
    best: dict[str, int] = {}
    for m in full_history(conn, swimmer_id, pool_type=pool_type):
        if m["event_id"] not in best or m["time_ms"] < best[m["event_id"]]:
            best[m["event_id"]] = m["time_ms"]
    return best


def swimmer_identity(conn, swimmer_id: str) -> dict | None:
    """Género y año de nacimiento más recientes del nadador (None si no existe)."""
    row = conn.execute(
        """SELECT swimmer_name, gender, birth_date, club, league FROM ranking_results WHERE swimmer_id = ?
           ORDER BY (birth_date IS NULL), result_date DESC LIMIT 1""", (swimmer_id,)).fetchone()
    return dict(row) if row else None


def role_permissions(conn, role_id: str | None) -> list[str]:
    """Permisos vigentes de un rol (vacío si el rol no existe)."""
    rows = conn.execute(
        "SELECT permission_key FROM role_permission WHERE role_id = ? ORDER BY permission_key", (role_id or "",)
    ).fetchall()
    return [r[0] for r in rows]


def role_exists(conn, role_id: str) -> bool:
    return conn.execute("SELECT 1 FROM app_role WHERE id = ?", (role_id,)).fetchone() is not None


def list_roles(conn) -> list[dict]:
    roles = conn.execute("SELECT id, name, is_system FROM app_role ORDER BY is_system DESC, name").fetchall()
    links: dict[str, list[str]] = {}
    for r in conn.execute("SELECT role_id, permission_key FROM role_permission ORDER BY permission_key").fetchall():
        links.setdefault(r[0], []).append(r[1])
    counts = {r[0]: r[1] for r in conn.execute("SELECT role, COUNT(*) FROM app_user GROUP BY role").fetchall()}
    return [{"id": r["id"], "name": r["name"], "is_system": bool(r["is_system"]),
             "permissions": links.get(r["id"], []), "users": counts.get(r["id"], 0)} for r in roles]


def save_role(conn, role_id: str, name: str, permissions: list[str], create: bool) -> None:
    """Crea o actualiza un rol y reemplaza sus permisos."""
    if create:
        conn.execute("INSERT INTO app_role (id, name, is_system) VALUES (?, ?, 0)", (role_id, name))
    else:
        conn.execute("UPDATE app_role SET name = ? WHERE id = ?", (name, role_id))
    conn.execute("DELETE FROM role_permission WHERE role_id = ?", (role_id,))
    for key in sorted(set(permissions)):
        conn.execute("INSERT INTO role_permission (role_id, permission_key) VALUES (?, ?)", (role_id, key))
    conn.commit()


def delete_role(conn, role_id: str) -> None:
    conn.execute("DELETE FROM role_permission WHERE role_id = ?", (role_id,))
    conn.execute("DELETE FROM app_role WHERE id = ?", (role_id,))
    conn.commit()


def list_permissions(conn) -> list[dict]:
    rows = conn.execute("SELECT key, label, is_system FROM app_permission ORDER BY is_system DESC, key").fetchall()
    counts = {r[0]: r[1] for r in conn.execute(
        "SELECT permission_key, COUNT(*) FROM role_permission GROUP BY permission_key").fetchall()}
    return [{"key": r["key"], "label": r["label"], "is_system": bool(r["is_system"]),
             "roles": counts.get(r["key"], 0)} for r in rows]


def permission_keys(conn) -> set[str]:
    return {r[0] for r in conn.execute("SELECT key FROM app_permission").fetchall()}


def create_permission(conn, key: str, label: str) -> None:
    from . import permisos

    conn.execute("INSERT INTO app_permission (key, label, is_system) VALUES (?, ?, 0)", (key, label))
    conn.execute("INSERT OR IGNORE INTO role_permission (role_id, permission_key) VALUES (?, ?)",
                 (permisos.ADMIN_ROLE, key))
    conn.commit()


def update_permission_label(conn, key: str, label: str) -> None:
    conn.execute("UPDATE app_permission SET label = ? WHERE key = ?", (label, key))
    conn.commit()


def delete_permission(conn, key: str) -> None:
    conn.execute("DELETE FROM role_permission WHERE permission_key = ?", (key,))
    conn.execute("DELETE FROM app_permission WHERE key = ?", (key,))
    conn.commit()


def get_user_by_id(conn, user_id: int):
    return conn.execute("SELECT * FROM app_user WHERE id = ?", (user_id,)).fetchone()


def list_users(conn, q: str | None = None, limit: int = 50) -> list[dict]:
    """Usuarios para administrar roles (sin datos de acceso), más recientes primero."""
    from . import auth

    where, params = "", []
    if q and q.strip():
        where, params = "WHERE email LIKE ?", [f"%{auth.normalize_email(q)}%"]
    rows = conn.execute(
        f"SELECT id, email, role, active, created_at FROM app_user {where} ORDER BY id DESC LIMIT ?",
        [*params, limit],
    ).fetchall()
    return [dict(r) for r in rows]


def count_active_admins(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM app_user WHERE role = 'admin' AND active = 1").fetchone()[0]


def set_role(conn: sqlite3.Connection, user_id: int, role: str) -> None:
    conn.execute("UPDATE app_user SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()


def set_active(conn, user_id: int, active: bool) -> None:
    conn.execute("UPDATE app_user SET active = ? WHERE id = ?", (1 if active else 0, user_id))
    conn.commit()


def swimmer_profile(
    conn: sqlite3.Connection,
    swimmer_id: str,
    pool_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    top: int = 5,
) -> dict | None:
    """Ficha del nadador: datos personales + las pruebas en las que está mejor
    ubicado en el ranking nacional de su categoría/género.

    Devuelve None si el nadador no tiene marcas en el rango. pool_type acota las
    pruebas consideradas (los datos personales se mantienen). top_events viene
    ordenado por puesto nacional ascendente; desempata por mayor número de
    competidores y luego por nombre de prueba."""
    ranks = swimmer_event_ranks(conn, swimmer_id, date_from, date_to)
    if not ranks:
        return None
    events = [r for r in ranks if not pool_type or r["pool_type"] == pool_type]
    events = sorted(
        events,
        key=lambda r: (r["national_rank"], -r["national_total"], r["event_name"]),
    )
    first = ranks[0]
    birth = conn.execute(
        """SELECT birth_date FROM ranking_results
           WHERE swimmer_id = ? AND birth_date IS NOT NULL
           ORDER BY result_date DESC LIMIT 1""",
        (swimmer_id,),
    ).fetchone()
    return {
        "swimmer_id": swimmer_id,
        "swimmer_name": first["swimmer_name"],
        "gender": first["gender"],
        "age": first["age"],
        "league": first["league"],
        "club": first["club"],
        "birth_date": birth["birth_date"] if birth else None,
        "reference_year": int(date_to[:4]) if date_to else date.today().year,
        "top_events": events[:top],
    }


# --- Cuenta: nadador vinculado, seguidos, contraseña y borrado --------------------

def swimmer_summary(conn, swimmer_id: str) -> dict | None:
    """{swimmer_id, swimmer_name, club, league} más reciente del nadador, o None."""
    row = conn.execute(
        """SELECT swimmer_id, swimmer_name, club, league FROM ranking_results
           WHERE swimmer_id = ? ORDER BY result_date DESC LIMIT 1""",
        (swimmer_id,),
    ).fetchone()
    return dict(row) if row else None


def verify_swimmer_birth(conn, swimmer_id: str, birth_date: str) -> bool:
    """True si la fecha de nacimiento (AAAA-MM-DD) coincide con la del nadador.

    FECNA a veces guarda la fecha con día y mes invertidos (5 de diciembre como 12 de mayo); un padre
    que escribe la fecha real no coincidiría nunca. Por eso también se acepta la fecha con día y mes
    intercambiados cuando eso es una fecha válida (día ≤ 12). Son como mucho dos candidatas por nadador,
    y el vínculo ya está limitado a 5 intentos por minuto."""
    candidates = [birth_date]
    parts = birth_date.split("-")
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit() and int(parts[2]) <= 12 and int(parts[1]) != int(parts[2]):
        candidates.append(f"{parts[0]}-{int(parts[2]):02d}-{int(parts[1]):02d}")
    marks = ", ".join("?" for _ in candidates)
    row = conn.execute(
        f"SELECT 1 FROM ranking_results WHERE swimmer_id = ? AND birth_date IN ({marks}) LIMIT 1",
        (swimmer_id, *candidates),
    ).fetchone()
    return row is not None


def set_user_swimmer(conn, user_id: int, swimmer_id: str | None) -> None:
    conn.execute("UPDATE app_user SET swimmer_id = ? WHERE id = ?", (swimmer_id, user_id))
    conn.commit()


def get_user_swimmer_id(conn, user_id: int) -> str | None:
    row = conn.execute("SELECT swimmer_id FROM app_user WHERE id = ?", (user_id,)).fetchone()
    return row["swimmer_id"] if row else None


def list_following(conn, user_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT swimmer_id, swimmer_name FROM swimmer_follow WHERE user_id = ? "
        "ORDER BY swimmer_name",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def tracked_swimmer_ids(conn) -> list[str]:
    """Nadadores seguidos por algún usuario o vinculados a una cuenta."""
    rows = conn.execute(
        "SELECT swimmer_id FROM swimmer_follow UNION "
        "SELECT swimmer_id FROM app_user WHERE swimmer_id IS NOT NULL AND swimmer_id <> ''"
    ).fetchall()
    return [r[0] for r in rows]


_HISTORY_COLUMNS = "event_id, event_name, pool_type, time_ms, result_date, points, tournament"


def event_names(conn) -> dict[str, str]:
    """event_id → nombre de la prueba, tal como aparece en el ranking."""
    rows = conn.execute("SELECT event_id, MAX(event_name) FROM ranking_results GROUP BY event_id").fetchall()
    return {r[0]: r[1] for r in rows}


def save_history(conn, swimmer_id: str, marks: list[dict], names: dict[str, str]) -> int:
    """Guarda las marcas del Historial Deportivo (con su torneo y puntos). Devuelve las nuevas."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    before = conn.execute("SELECT COUNT(*) FROM swimmer_mark WHERE swimmer_id = ?", (swimmer_id,)).fetchone()[0]
    for m in marks:
        name = names.get(m["event_id"])
        if not name:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO swimmer_mark (swimmer_id, event_id, event_name, pool_type, time_ms, result_date, "
            "points, tournament, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (swimmer_id, m["event_id"], name, m["pool"], m["time_ms"], m["date"], m.get("points"), m.get("tournament"), now))
        conn.execute(
            "UPDATE swimmer_mark SET tournament = ?, points = COALESCE(?, points) WHERE swimmer_id = ? AND event_id = ? "
            "AND pool_type = ? AND time_ms = ? AND result_date = ?",
            (m.get("tournament"), m.get("points"), swimmer_id, m["event_id"], m["pool"], m["time_ms"], m["date"]))
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM swimmer_mark WHERE swimmer_id = ?", (swimmer_id,)).fetchone()[0]
    return after - before


def swimmer_history_status(conn, swimmer_id: str) -> dict | None:
    """Estado del historial completo de un nadador (None si no existe): total de marcas y última descarga."""
    if not conn.execute("SELECT 1 FROM ranking_results WHERE swimmer_id = ? LIMIT 1", (swimmer_id,)).fetchone():
        return None
    row = conn.execute("SELECT COUNT(*), MAX(fetched_at) FROM swimmer_mark WHERE swimmer_id = ?", (swimmer_id,)).fetchone()
    total = conn.execute("SELECT COUNT(*) FROM ranking_results WHERE swimmer_id = ?", (swimmer_id,)).fetchone()[0]
    return {"ranking_marks": total, "extra_marks": row[0], "last_fetched": row[1]}


def full_history(conn, swimmer_id: str, event_id: str | None = None, pool_type: str | None = None) -> list[dict]:
    """Marcas del ranking más las del Historial Deportivo que el ranking no trae, por fecha."""
    where, params = "", []
    if event_id:
        where += " AND event_id = ?"
        params.append(event_id)
    if pool_type:
        where += " AND pool_type = ?"
        params.append(pool_type)
    sql = f"""
        SELECT {_HISTORY_COLUMNS} FROM ranking_results WHERE swimmer_id = ? {where}
        UNION ALL
        SELECT {_HISTORY_COLUMNS} FROM swimmer_mark m WHERE m.swimmer_id = ? {where}
          AND NOT EXISTS (SELECT 1 FROM ranking_results r WHERE r.swimmer_id = m.swimmer_id AND r.event_id = m.event_id
                          AND r.pool_type = m.pool_type AND r.time_ms = m.time_ms AND r.result_date = m.result_date)
        ORDER BY result_date ASC, time_ms ASC"""
    rows = conn.execute(sql, [swimmer_id, *params, swimmer_id, *params]).fetchall()
    return [dict(r) for r in rows]


def swimmer_event_ids(conn, swimmer_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT event_id FROM ranking_results WHERE swimmer_id = ?", (swimmer_id,)
    ).fetchall()
    return [r[0] for r in rows]


def set_tournaments(conn, swimmer_id: str, marks: list[dict]) -> int:
    """Guarda el torneo de las marcas ya conocidas (misma prueba, piscina, tiempo y fecha).
    Devuelve cuántas marcas quedaron con torneo."""
    done = 0
    for m in marks:
        cur = conn.execute(
            "UPDATE ranking_results SET tournament = ? WHERE swimmer_id = ? AND event_id = ? "
            "AND pool_type = ? AND time_ms = ? AND result_date = ? "
            "AND (tournament IS NULL OR tournament <> ?)",
            (m["tournament"], swimmer_id, m["event_id"], m["pool"], m["time_ms"], m["date"], m["tournament"]),
        )
        done += cur.rowcount or 0
    conn.commit()
    return done


def follow_swimmer(conn, user_id: int, swimmer_id: str, swimmer_name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO swimmer_follow (user_id, swimmer_id, swimmer_name) "
        "VALUES (?, ?, ?)",
        (user_id, swimmer_id, swimmer_name),
    )
    conn.commit()


def unfollow_swimmer(conn, user_id: int, swimmer_id: str) -> None:
    conn.execute(
        "DELETE FROM swimmer_follow WHERE user_id = ? AND swimmer_id = ?",
        (user_id, swimmer_id),
    )
    conn.commit()


def change_password(conn, user_id: int, current: str, new: str) -> None:
    """Cambia la contraseña tras validar la actual. ValueError con mensaje en español."""
    from . import auth

    row = conn.execute(
        "SELECT password_hash, salt FROM app_user WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None or not auth.verify_password(current, row["password_hash"], row["salt"]):
        raise ValueError("La contraseña actual no es correcta.")
    err = auth.valid_password(new)
    if err:
        raise ValueError(err)
    import time

    hash_hex, salt_hex = auth.hash_password(new)
    conn.execute(  # password_changed_at invalida los tokens emitidos antes (api/security.py)
        "UPDATE app_user SET password_hash = ?, salt = ?, password_changed_at = ? WHERE id = ?",
        (hash_hex, salt_hex, int(time.time()), user_id),
    )
    conn.commit()


# --- Recuperar contraseña ---------------------------------------------------------
RESET_TTL = 15 * 60       # el código vence a los 15 minutos
RESET_RESEND = 60         # no se envía otro antes de 1 minuto
RESET_MAX_ATTEMPTS = 5    # con 5 intentos fallidos el código se anula
RESET_INVALID = "El código no es válido o ya venció. Pide uno nuevo."


def start_password_reset(conn, email: str, now: int) -> tuple[dict, str] | None:
    """Genera un código de 6 dígitos para una cuenta activa y guarda solo su hash.

    Devuelve (usuario, código) para enviarlo por correo, o None si no hay que enviar nada:
    la cuenta no existe, está desactivada o ya se envió uno hace menos de RESET_RESEND.
    Quien llama responde igual en todos los casos: no revela qué correos tienen cuenta."""
    import secrets

    from . import auth

    user = get_user_by_email(conn, email)
    if user is None or not user["active"]:
        return None
    prev = conn.execute("SELECT sent_at FROM password_reset WHERE user_id = ?", (user["id"],)).fetchone()
    if prev and now - int(prev["sent_at"]) < RESET_RESEND:
        return None
    code = f"{secrets.randbelow(10**6):06d}"
    code_hash, salt = auth.hash_password(code)
    conn.execute("DELETE FROM password_reset WHERE user_id = ?", (user["id"],))
    conn.execute(
        "INSERT INTO password_reset (user_id, code_hash, salt, expires_at, attempts, sent_at)"
        " VALUES (?, ?, ?, ?, 0, ?)",
        (user["id"], code_hash, salt, now + RESET_TTL, now),
    )
    conn.commit()
    return dict(user), code


def finish_password_reset(conn, email: str, code: str, new_password: str, now: int) -> dict:
    """Cambia la contraseña si el código es correcto y vigente. Devuelve el usuario.

    ValueError con mensaje en español si no. Cada intento fallido cuenta; al llegar a
    RESET_MAX_ATTEMPTS el código se borra. El cambio cierra las demás sesiones
    (password_changed_at), igual que change_password."""
    from . import auth

    err = auth.valid_password(new_password)
    if err:  # antes de mirar el código: un error de formato no gasta intentos
        raise ValueError(err)
    user = get_user_by_email(conn, email)
    reset = None
    if user is not None and user["active"]:
        reset = conn.execute("SELECT * FROM password_reset WHERE user_id = ?", (user["id"],)).fetchone()
    if reset is None or now > int(reset["expires_at"]):
        auth.hash_password(code or "")  # mismo costo de PBKDF2 que el camino normal
        raise ValueError(RESET_INVALID)
    if not auth.verify_password((code or "").strip(), reset["code_hash"], reset["salt"]):
        attempts = int(reset["attempts"]) + 1
        if attempts >= RESET_MAX_ATTEMPTS:
            conn.execute("DELETE FROM password_reset WHERE user_id = ?", (user["id"],))
        else:
            conn.execute("UPDATE password_reset SET attempts = ? WHERE user_id = ?", (attempts, user["id"]))
        conn.commit()
        raise ValueError(RESET_INVALID)
    hash_hex, salt_hex = auth.hash_password(new_password)
    conn.execute(
        "UPDATE app_user SET password_hash = ?, salt = ?, password_changed_at = ? WHERE id = ?",
        (hash_hex, salt_hex, now, user["id"]),
    )
    conn.execute("DELETE FROM password_reset WHERE user_id = ?", (user["id"],))
    conn.commit()
    return dict(get_user_by_email(conn, email))


def delete_user(conn, user_id: int) -> None:
    """Borra la cuenta y todo lo asociado (seguidos, vigilancia, vínculo)."""
    for table in ("swimmer_follow", "competition_watch", "password_reset"):
        conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM app_user WHERE id = ?", (user_id,))
    conn.commit()
