"""CLI del agente: fetch, best, compare, ranking, history."""

import argparse
import logging
import sys
from datetime import date

from . import db as database
from . import extractor, normalizer
from .times import ms_to_time


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    conn = database.connect(args.db)
    try:
        return args.func(conn, args)
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fecna_agent")
    parser.add_argument("--db", default=database.DEFAULT_DB_PATH, help="Ruta de la base SQLite")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("fetch", help="Extraer ranking desde FECNA y guardarlo")
    p.add_argument("--inicio", default="2024-01-01")
    p.add_argument("--fin", default=date.today().isoformat())
    p.add_argument("--genero", default="")
    p.add_argument("--categoria", default="")
    p.add_argument("--prueba", default="")
    p.add_argument("--piscina", default="")
    p.add_argument("--torneo", default="")
    p.add_argument("--liga", default="")
    p.add_argument("--master", default="0")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("best", help="Mejor marca de un nadador")
    p.add_argument("swimmer_id")
    p.add_argument("--prueba", dest="event_id")
    p.add_argument("--piscina", dest="pool_type")
    p.add_argument("--desde", help="Fecha mínima del resultado (YYYY-MM-DD)")
    p.add_argument("--hasta", help="Fecha máxima del resultado (YYYY-MM-DD)")
    p.set_defaults(func=cmd_best)

    p = sub.add_parser("compare", help="Comparar dos nadadores en una prueba")
    p.add_argument("swimmer_a")
    p.add_argument("swimmer_b")
    p.add_argument("--prueba", dest="event_id", required=True)
    p.add_argument("--piscina", dest="pool_type")
    p.add_argument("--desde", help="Fecha mínima del resultado (YYYY-MM-DD)")
    p.add_argument("--hasta", help="Fecha máxima del resultado (YYYY-MM-DD)")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("ranking", help="Ranking por mejor marca")
    p.add_argument("--prueba", dest="event_id", required=True)
    p.add_argument("--piscina", dest="pool_type")
    p.add_argument("--genero", dest="gender")
    p.add_argument("--categoria", help="Etiqueta de categoría, ej. '12 AÑOS'")
    p.add_argument("--liga", help="Nombre exacto de la liga, ej. ANTIOQUIA")
    p.add_argument("--desde", help="Fecha mínima del resultado (YYYY-MM-DD)")
    p.add_argument("--hasta", help="Fecha máxima del resultado (YYYY-MM-DD)")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_ranking)

    p = sub.add_parser(
        "swimrank",
        help="Puesto de un nadador en cada prueba, a nivel de su liga y nacional",
    )
    p.add_argument("swimmer_id")
    p.add_argument("--desde", help="Fecha mínima del resultado (YYYY-MM-DD)")
    p.add_argument("--hasta", help="Fecha máxima del resultado (YYYY-MM-DD)")
    p.set_defaults(func=cmd_swimrank)

    p = sub.add_parser("history", help="Evolución de marcas de un nadador")
    p.add_argument("swimmer_id")
    p.add_argument("--prueba", dest="event_id")
    p.add_argument("--piscina", dest="pool_type")
    p.add_argument("--desde", help="Fecha mínima del resultado (YYYY-MM-DD)")
    p.add_argument("--hasta", help="Fecha máxima del resultado (YYYY-MM-DD)")
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("catalog", help="Descargar catálogos (pruebas, categorías, ...)")
    p.set_defaults(func=cmd_catalog)

    p = sub.add_parser(
        "sync",
        help="Sincronización masiva: todas las pruebas × piscinas × géneros",
    )
    p.add_argument("--inicio", default="2024-01-01",
                   help="Para verificar un campeonato, usa su fecha de inicio")
    p.add_argument("--fin", default=date.today().isoformat())
    p.add_argument("--piscina", choices=["LC", "SC"], action="append",
                   help="Repetible; defecto: ambas")
    p.add_argument("--genero", choices=["M", "F"], action="append",
                   help="Repetible; defecto: ambos")
    p.add_argument("--prueba", action="append",
                   help="IDs de prueba específicos; defecto: todas las del catálogo")
    p.add_argument("--categoria", default="", help="Vacío = todas")
    p.add_argument("--delay", type=float, default=0.6,
                   help="Pausa en segundos entre peticiones")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("recent", help="Novedades de la última sincronización")
    p.add_argument("--limit", type=int, default=30, help="Máximo de resultados a listar")
    p.set_defaults(func=cmd_recent)

    p = sub.add_parser(
        "anonymize",
        help="Crear copia anonimizada de la base para publicar (sin cédula ni fecha exacta)",
    )
    p.add_argument("--out", default="data/fecna_public.db", help="Ruta de salida")
    p.set_defaults(func=cmd_anonymize)

    p = sub.add_parser("index", help="Construir índice semántico (pruebas y nadadores)")
    p.add_argument("--embeddings", choices=["hash", "default"], default="hash",
                   help="'default' usa MiniLM de ChromaDB (descarga modelo)")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("ask", help="Pregunta en lenguaje natural")
    p.add_argument("question")
    p.add_argument("--llm", action="store_true",
                   help="Redactar la respuesta con Ollama (los datos siguen siendo SQL/Python)")
    p.add_argument("--model", default=None, help="Modelo de Ollama (defecto: primero instalado)")
    p.set_defaults(func=cmd_ask)

    return parser


def cmd_fetch(conn, args) -> int:
    raw = extractor.fetch_ranking(
        inicio=args.inicio, fin=args.fin, genero=args.genero,
        categoria=args.categoria, prueba=args.prueba, piscina=args.piscina,
        torneo=args.torneo, liga=args.liga, master=args.master,
    )
    rows = normalizer.normalize_rows(raw)
    inserted = database.insert_results(conn, rows)
    print(f"Recibidos: {len(raw)} | Válidos: {len(rows)} | Nuevos insertados: {inserted}")
    return 0


def cmd_best(conn, args) -> int:
    row = database.best_time(conn, args.swimmer_id, args.event_id, args.pool_type,
                             args.desde, args.hasta)
    if not row:
        print("Sin resultados para ese nadador/filtros.")
        return 1
    print(f"{row['swimmer_name']} ({row['swimmer_id']})")
    print(f"  {row['event_name']} [{row['pool_type']}]: {row['time_raw']} ({row['result_date']})")
    return 0


def cmd_compare(conn, args) -> int:
    result = database.compare_swimmers(
        conn, args.swimmer_a, args.swimmer_b, args.event_id, args.pool_type,
        args.desde, args.hasta,
    )
    a, b = result["a"], result["b"]
    for label, row, sid in (("A", a, args.swimmer_a), ("B", b, args.swimmer_b)):
        if not row:
            print(f"Nadador {label} ({sid}): sin resultados para esos filtros.")
    if not (a and b):
        return 1

    faster, slower = (a, b) if a["time_ms"] <= b["time_ms"] else (b, a)
    print(f"En {a['event_name']} [{a['pool_type'] or ''}], "
          f"{faster['swimmer_name']} tiene mejor marca que {slower['swimmer_name']}.")
    print()
    print(f"  {a['swimmer_name']}: {a['time_raw']} ({a['result_date']})")
    print(f"  {b['swimmer_name']}: {b['time_raw']} ({b['result_date']})")
    print(f"  Diferencia: {result['diff_ms'] / 1000:.2f} segundos "
          f"({result['diff_ms'] / slower['time_ms'] * 100:.2f}%).")
    return 0


def cmd_ranking(conn, args) -> int:
    from .categories import age_range

    rows = database.ranking(
        conn, args.event_id, args.pool_type, args.gender, args.limit,
        league=args.liga,
        age_range=age_range(args.categoria) if args.categoria else None,
        date_from=args.desde,
        date_to=args.hasta,
    )
    if not rows:
        print("Sin resultados para esos filtros.")
        return 1
    for pos, row in enumerate(rows, 1):
        print(f"{pos:>3}. {ms_to_time(row['time_ms'])}  {row['swimmer_name']}"
              f"  ({row['club']} / {row['league']})")
    return 0


def cmd_swimrank(conn, args) -> int:
    rows = database.swimmer_event_ranks(conn, args.swimmer_id, args.desde, args.hasta)
    if not rows:
        print("Sin marcas para ese nadador en el rango indicado.")
        return 1
    league_name = next((r["league"] for r in rows if r["league"]), None)
    print(f"Rankings de {rows[0]['swimmer_name']} ({args.swimmer_id}) "
          f"— liga: {league_name or '—'} · categoría: {rows[0]['age']} años")
    print("(puesto por género y categoría: liga · Colombia)\n")
    for r in rows:
        liga = f"{r['league_rank']}/{r['league_total']}" if r["league"] else "—"
        print(f"  {r['event_name']} [{r['pool_type']}/{r['gender']}]  "
              f"{ms_to_time(r['best_ms'])}  — liga {liga} · "
              f"Colombia {r['national_rank']}/{r['national_total']}")
    return 0


def cmd_history(conn, args) -> int:
    rows = database.history(conn, args.swimmer_id, args.event_id, args.pool_type,
                            args.desde, args.hasta)
    if not rows:
        print("Sin resultados para ese nadador/filtros.")
        return 1
    print(f"{rows[0]['swimmer_name']} ({args.swimmer_id})")
    for row in rows:
        print(f"  {row['result_date']}  {row['time_raw']}  "
              f"{row['event_name']} [{row['pool_type']}]")
    return 0


def cmd_catalog(conn, args) -> int:
    from . import catalog

    catalogs = catalog.fetch_catalogs()
    total = database.save_catalogs(conn, catalogs)
    for kind, entries in catalogs.items():
        print(f"{kind}: {len(entries)} opciones")
    print(f"Total guardado: {total}")
    return 0


def cmd_index(conn, args) -> int:
    from . import semantic  # import perezoso: chromadb tarda en cargar

    print(semantic.rebuild_from_db(conn, args.embeddings))
    return 0


def cmd_sync(conn, args) -> int:
    from . import sync

    events = None
    if args.prueba:
        catalog_events = dict(database.get_catalog(conn, "prueba"))
        events = [(eid, catalog_events.get(eid, eid)) for eid in args.prueba]

    def progress(done, total, detail):
        event_name, pool, gender, received, inserted, error = detail
        status = f"ERROR: {error}" if error else f"{received} recibidos, {inserted} nuevos"
        print(f"[{done:>3}/{total}] {event_name} {pool} {gender}: {status}")

    stats = sync.sync_all(
        conn, inicio=args.inicio, fin=args.fin, events=events,
        pools=tuple(args.piscina or ("LC", "SC")),
        genders=tuple(args.genero or ("M", "F")),
        categoria=args.categoria, delay=args.delay, progress=progress,
    )
    print(f"\nSincronización {args.inicio} → {args.fin}: "
          f"{stats['combos']} combinaciones, {stats['received']} recibidos, "
          f"{stats['inserted']} nuevos, {stats['errors']} errores.")
    if stats["aborted"]:
        print(f"\nABORTADA: {stats['aborted']}")

    if stats["inserted"]:
        from . import semantic
        print(semantic.rebuild_from_db(conn))
        print("\nNovedades por prueba (ver detalle con 'recent'):")
        for row in database.summarize_run(conn, stats["run_at"]):
            print(f"  {row['event_name']} [{row['pool_type']}/{row['gender']}]: "
                  f"{row['nuevos']} nuevos")
    return 1 if stats["aborted"] or (stats["errors"] and not stats["received"]) else 0


def cmd_anonymize(conn, args) -> int:
    from pathlib import Path

    n = database.export_anonymized(conn, args.out)
    print(f"Base anonimizada escrita en {args.out} ({n} resultados).")
    print("Esta copia es la que puedes publicar; la base original no se toca.")
    return 0


def cmd_recent(conn, args) -> int:
    last = database.last_sync(conn)
    if not last:
        print("No hay sincronizaciones registradas. Ejecuta: python -m fecna_agent sync")
        return 1
    print(f"Última sincronización: {last['run_at']} "
          f"(rango {last['inicio']} → {last['fin']}, {last['inserted']} nuevos, "
          f"{last['errors']} errores)")
    rows = database.results_from_run(conn, last["run_at"])
    if not rows:
        print("Sin resultados nuevos en esa corrida: la base ya estaba al día.")
        return 0
    for row in rows[: args.limit]:
        print(f"  {row['result_date']}  {row['time_raw']}  {row['swimmer_name']}"
              f"  — {row['event_name']} [{row['pool_type']}/{row['gender']}] {row['club']}")
    if len(rows) > args.limit:
        print(f"  ... y {len(rows) - args.limit} más (usa --limit)")
    return 0


def cmd_ask(conn, args) -> int:
    from . import agent  # import perezoso: chromadb tarda en cargar

    print(agent.answer(conn, args.question, use_llm=args.llm, llm_model=args.model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
