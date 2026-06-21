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

  UNIQUE (swimmer_id, event_id, pool_type, time_ms, result_date)
);
CREATE INDEX IF NOT EXISTS idx_results_swimmer ON ranking_results (swimmer_id);
CREATE INDEX IF NOT EXISTS idx_results_event ON ranking_results (event_id, pool_type);

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


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Migraciones suaves para bases creadas con un esquema anterior."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(competition)")}
    if "content_hash" not in cols:
        conn.execute("ALTER TABLE competition ADD COLUMN content_hash TEXT")
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
                  "? - CAST(strftime('%Y', birth_date) AS INTEGER) BETWEEN ? AND ?")
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
            ) WHERE rn = 1""",
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
                  "? - CAST(strftime('%Y', birth_date) AS INTEGER) BETWEEN ? AND ?")
        params.extend([reference_year, *age_range])
    return conn.execute(
        f"""SELECT swimmer_id, swimmer_name, gender, birth_date, club, league,
                   MIN(time_ms) AS time_ms, time_raw, result_date
            FROM ranking_results
            WHERE 1=1 {where}
            GROUP BY swimmer_id
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
            ) WHERE rn = 1
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
            ) WHERE rn = 1
        ),
        best AS (
            SELECT f.swimmer_id, f.swimmer_name, f.event_id, f.event_name,
                   f.pool_type, f.gender, sl.league AS league, sc.club AS club,
                   ? - CAST(strftime('%Y', f.birth_date) AS INTEGER) AS age,
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
    if swimmer_name:
        where += " AND swimmer_name = ?"
        params.append(swimmer_name)
    return conn.execute(
        f"""SELECT * FROM competition_entry
            WHERE competition_id = ? {where}
            ORDER BY session_date IS NULL, session_date,
                     start_time IS NULL, start_time, event_number, heat, lane""",
        params,
    ).fetchall()


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
