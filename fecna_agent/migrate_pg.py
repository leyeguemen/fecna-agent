"""Copia una base SQLite local a PostgreSQL (Supabase).

Uso:
    python -m fecna_agent.migrate_pg --source data/fecna.db --dry-run
    python -m fecna_agent.migrate_pg --source data/fecna.db

La URL de destino se lee de la variable de entorno DATABASE_URL (o del archivo
.env). Nunca se imprime ni se acepta por argumento. Es idempotente: las filas ya
existentes se ignoran (ON CONFLICT DO NOTHING).
"""

import argparse
import os
import sqlite3
import sys

from . import db, pg

# Orden respeta claves foráneas. app_user solo con --include-users.
TABLES = ["ranking_results", "catalogs", "sync_log", "competition",
          "competition_entry", "competition_watch"]
SERIAL = {"sync_log": "id", "competition": "id", "competition_entry": "id",
          "app_user": "id"}
BATCH = 1000


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _src_columns(src: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in src.execute(f"PRAGMA table_info({table})")]


def migrate(source: str, dry_run: bool, include_users: bool) -> int:
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    tables = TABLES + (["app_user"] if include_users else [])

    dest = None
    if not dry_run:
        _load_env()
        url = os.environ.get("DATABASE_URL")
        if not url or not pg.is_pg_url(url):
            print("Falta DATABASE_URL (postgresql://...) en el entorno o en .env")
            return 2
        dest = db.connect(url)  # crea el esquema si no existe

    for table in tables:
        cols = _src_columns(src, table)
        if not cols:
            print(f"{table}: no existe en el origen, se omite")
            continue
        total = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if dry_run:
            print(f"{table}: {total} filas (dry-run)")
            continue
        names = ", ".join(cols)
        marks = ", ".join(f":{c}" for c in cols)
        sql = f"INSERT OR IGNORE INTO {table} ({names}) VALUES ({marks})"
        cur = src.execute(f"SELECT {names} FROM {table}")
        done = 0
        while True:
            chunk = cur.fetchmany(BATCH)
            if not chunk:
                break
            dest.executemany(sql, [dict(r) for r in chunk])
            dest.commit()
            done += len(chunk)
        if table in SERIAL:
            col = SERIAL[table]
            dest.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                f"COALESCE((SELECT MAX({col}) FROM {table}), 1))"
            )
            dest.commit()
        after = dest.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: origen {total} · destino {after}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default=str(db.DEFAULT_DB_PATH))
    ap.add_argument("--dry-run", action="store_true",
                    help="solo cuenta filas del origen, sin conectar a Postgres")
    ap.add_argument("--include-users", action="store_true",
                    help="copia también app_user (cuentas y hashes)")
    a = ap.parse_args(argv)
    return migrate(a.source, a.dry_run, a.include_users)


if __name__ == "__main__":
    sys.exit(main())
