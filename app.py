"""Interfaz Streamlit del agente FECNA (Fase 4).

Ejecutar:  streamlit run app.py
"""

# En la nube (Linux) ChromaDB exige sqlite >= 3.35: se reemplaza el módulo
# sqlite3 por pysqlite3 ANTES de importar chromadb. En local no hace nada.
try:
    __import__("pysqlite3")
    import sys

    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import datetime as dt
import hashlib
import os
import re

import pandas as pd
import streamlit as st

from fecna_agent import agent, categories, export
from fecna_agent import catalog as catalog_mod
from fecna_agent import db as database
from fecna_agent import extractor, normalizer, semantic
from fecna_agent.times import ms_to_time

st.set_page_config(page_title="FECNA Natación", page_icon="🏊", layout="wide")


# --- Modo público: anonimiza identificación y fecha de nacimiento ---
# Se activa con la variable de entorno FECNA_PUBLIC o el secreto del mismo
# nombre (Streamlit Cloud). En local queda desactivado: la app va completa.
def _public_mode() -> bool:
    if os.environ.get("FECNA_PUBLIC"):
        return True
    try:
        return bool(st.secrets.get("FECNA_PUBLIC", False))
    except Exception:
        return False


PUBLIC = _public_mode()

_ID_RE = re.compile(r"\b\d{6,12}\b")


def mask_id(swimmer_id) -> str:
    """Código pseudónimo estable, no reversible, para distinguir homónimos."""
    digest = hashlib.sha1(str(swimmer_id).encode()).hexdigest()[:5].upper()
    return f"#{digest}"


def fmt_swimmer(s) -> str:
    """Etiqueta de un nadador (id, nombre) para los selectores."""
    return f"{s[1]} ({mask_id(s[0]) if PUBLIC else s[0]})"


def redact(text: str) -> str:
    """Oculta números de identificación en texto libre (modo público)."""
    return _ID_RE.sub("·····", text) if PUBLIC else text


def _resolve_db_path():
    """Base a usar: FECNA_DB si está; si no, la cruda local; y como respaldo en
    la nube (donde la cruda no se sube), la anonimizada."""
    if os.environ.get("FECNA_DB"):
        return os.environ["FECNA_DB"]
    if database.DEFAULT_DB_PATH.exists():
        return database.DEFAULT_DB_PATH
    public = database.DEFAULT_DB_PATH.parent / "fecna_public.db"
    return public if public.exists() else database.DEFAULT_DB_PATH


conn = database.connect(_resolve_db_path())


@st.cache_resource
def ensure_semantic_index() -> str | None:
    """Reconstruye el índice semántico si falta (p. ej. al desplegar subiendo
    solo la base de datos). Se ejecuta una sola vez por arranque."""
    try:
        client = semantic.get_client()
        if client.get_collection(semantic.EVENTS_COLLECTION).count() > 0:
            return None
    except Exception:
        pass
    if database.get_catalog(conn, "prueba") and database.list_events(conn):
        return semantic.rebuild_from_db(conn)
    return None


ensure_semantic_index()


def rows_to_df(rows, columns=None) -> pd.DataFrame:
    df = pd.DataFrame([dict(row) for row in rows])
    return df[columns] if columns is not None and not df.empty else df


def event_options(prefer_local: bool = True) -> list[tuple[str, str]]:
    """Pruebas para los selects: las que tienen datos locales, o el catálogo."""
    local = database.list_events(conn) if prefer_local else []
    return local or database.get_catalog(conn, "prueba")


def rebuild_index() -> str:
    return semantic.rebuild_from_db(conn)


def history_df(swimmer_id: str, event_id: str | None, pool: str | None,
               date_from: str | None = None, date_to: str | None = None) -> pd.DataFrame:
    rows = database.history(conn, swimmer_id, event_id, pool, date_from, date_to)
    df = rows_to_df(rows)
    if not df.empty:
        df["segundos"] = df["time_ms"] / 1000
        df["fecha"] = pd.to_datetime(df["result_date"])
    return df


# ---------------- Barra lateral: datos y extracción ----------------

def admin_controls():
    """Controles de extracción/sincronización. Ocultos en modo público para que
    la app desplegada sea de solo lectura."""
    st.divider()
    st.subheader("Extraer desde FECNA")

    catalog_events = database.get_catalog(conn, "prueba")
    if not catalog_events:
        st.info("Sin catálogo de pruebas: descárgalo abajo.")
    event_pick = st.selectbox(
        "Prueba", catalog_events, format_func=lambda e: e[1], key="fetch_event",
    ) if catalog_events else None

    pool_pick = st.selectbox("Piscina", ["LC", "SC"], key="fetch_pool")
    gender_pick = st.selectbox("Género", ["M", "F"], key="fetch_gender")
    category_pick = st.text_input("Categoría (ej. 12 AÑOS, vacío = todas)", key="fetch_cat")
    date_from = st.date_input("Desde", dt.date(2024, 1, 1), key="fetch_from")
    date_to = st.date_input("Hasta", dt.date.today(), key="fetch_to")

    if st.button("Extraer y guardar", disabled=event_pick is None):
        with st.spinner("Consultando FECNA..."):
            try:
                raw = extractor.fetch_ranking(
                    inicio=date_from.isoformat(), fin=date_to.isoformat(),
                    genero=gender_pick, categoria=category_pick,
                    prueba=event_pick[0], piscina=pool_pick,
                )
                inserted = database.insert_results(conn, normalizer.normalize_rows(raw))
                st.success(f"{len(raw)} recibidos, {inserted} nuevos guardados.")
                st.info(rebuild_index())
            except Exception as exc:
                st.error(f"Error de extracción: {exc}")

    st.divider()
    st.subheader("Sincronización masiva")
    sync_from = st.date_input("Sincronizar desde", dt.date(2024, 1, 1), key="sync_from",
                              help="Para verificar un campeonato, usa su fecha de inicio")
    if st.button("Sincronizar todo (pruebas × piscinas × géneros)"):
        from fecna_agent import sync as sync_mod

        bar = st.progress(0.0, text="Sincronizando...")

        def on_progress(done, total, detail):
            event_name, pool, gender, received, inserted, error = detail
            bar.progress(done / total, text=f"{event_name} {pool} {gender} "
                                            f"({done}/{total})")

        try:
            stats = sync_mod.sync_all(conn, inicio=sync_from.isoformat(),
                                      progress=on_progress)
            bar.empty()
            if stats["aborted"]:
                st.error(f"Sincronización abortada: {stats['aborted']}")
            else:
                st.success(f"{stats['received']} recibidos, {stats['inserted']} nuevos, "
                           f"{stats['errors']} errores.")
            if stats["inserted"]:
                st.info(rebuild_index())
        except Exception as exc:
            bar.empty()
            st.error(f"Error de sincronización: {exc}")

    last = database.last_sync(conn)
    if last:
        st.caption(f"Última sincronización: {last['run_at'][:16]} · "
                   f"{last['inserted']} nuevos · {last['errors']} errores")

    st.divider()
    if st.button("Descargar catálogos"):
        with st.spinner("Descargando catálogos..."):
            saved = database.save_catalogs(conn, catalog_mod.fetch_catalogs())
            st.success(f"{saved} entradas de catálogo guardadas.")
    if st.button("Reconstruir índice semántico"):
        st.success(rebuild_index())


with st.sidebar:
    st.header("🏊 Datos locales")
    total = conn.execute("SELECT COUNT(*) FROM ranking_results").fetchone()[0]
    swimmers_count = len(database.list_swimmers(conn))
    events_count = len(database.list_events(conn))
    st.write(f"**{total}** resultados · **{swimmers_count}** nadadores · "
             f"**{events_count}** pruebas con datos")

    if PUBLIC:
        st.caption("Vista pública de solo lectura · datos anonimizados.")
    else:
        admin_controls()

# ---------------- Pestañas principales ----------------

tab_ask, tab_rank, tab_comp, tab_evo, tab_swrank, tab_new = st.tabs(
    ["💬 Pregunta", "🏆 Ranking", "⚖️ Comparar", "📈 Evolución",
     "🎖️ Rankings del nadador", "🆕 Novedades"]
)

with tab_ask:
    st.subheader("Pregunta en lenguaje natural")
    question = st.text_input(
        "Pregunta",
        placeholder="Compara el nadador 1105388915 con el 1094060609 en 50 libre piscina larga",
        label_visibility="collapsed",
    )

    from fecna_agent import llm

    ollama_up = llm.is_available()
    col_llm, col_model = st.columns([1, 2])
    use_llm = col_llm.toggle(
        "Redactar con IA local", value=False, disabled=not ollama_up,
        help="Usa Ollama para redactar; los cálculos siguen siendo SQL/Python.",
    )
    model = None
    if ollama_up and use_llm:
        model = col_model.selectbox("Modelo", llm.list_models(), label_visibility="collapsed")
    elif not ollama_up:
        col_model.caption("Ollama no está corriendo: respuestas determinísticas.")

    if question:
        with st.spinner("Consultando..."):
            st.code(redact(agent.answer(conn, question, use_llm=use_llm, llm_model=model)),
                    language=None)
        st.caption("Los cálculos siempre se hacen en SQL/Python sobre la base local; "
                   "el LLM solo redacta y los datos calculados se muestran junto a "
                   "su respuesta.")

with tab_rank:
    events = event_options()
    if not events:
        st.info("No hay datos locales. Extrae una prueba desde la barra lateral.")
    else:
        col1, col2, col3 = st.columns(3)
        event = col1.selectbox("Prueba", events, format_func=lambda e: e[1])
        pool = col2.selectbox("Piscina", ["Todas", "LC", "SC"])
        gender = col3.selectbox("Género", ["Todos", "M", "F"])

        col4, col5, col6 = st.columns(3)
        category_opts = ["Todas"] + [label for _, label in
                                     database.get_catalog(conn, "categoria_M")]
        category = col4.selectbox("Categoría", category_opts,
                                  help="Categoría FECNA: año del filtro 'Hasta' "
                                       "menos año de nacimiento")
        league_opts = ["Todas"] + database.list_leagues(conn)
        league = col5.selectbox("Liga", league_opts)
        limit = col6.slider("Tope", 5, 100, 20)

        col7, col8 = st.columns(2)
        rank_from = col7.date_input("Desde", dt.date(2024, 1, 1), key="rank_from",
                                    help="Acota la fecha del resultado: útil para "
                                         "el ranking de un campeonato o temporada")
        rank_to = col8.date_input("Hasta", dt.date.today(), key="rank_to")

        rows = database.ranking(
            conn, event[0],
            None if pool == "Todas" else pool,
            None if gender == "Todos" else gender,
            limit,
            league=None if league == "Todas" else league,
            age_range=None if category == "Todas" else categories.age_range(category),
            date_from=rank_from.isoformat(),
            date_to=rank_to.isoformat(),
        )
        if not rows:
            st.warning("Sin resultados para esos filtros.")
        else:
            df = rows_to_df(rows)
            df.insert(0, "puesto", range(1, len(df) + 1))
            df["tiempo"] = df["time_ms"].map(ms_to_time)
            cols = ["puesto", "tiempo", "swimmer_name", "birth_date", "club",
                    "league", "result_date"]
            if PUBLIC:
                cols.remove("birth_date")  # no exponer fecha de nacimiento
            shown = df[cols].rename(columns={
                "puesto": "Puesto", "tiempo": "Tiempo", "swimmer_name": "Nadador",
                "birth_date": "F. nac.", "club": "Club", "league": "Liga",
                "result_date": "Fecha",
            })
            st.dataframe(shown, hide_index=True, width="stretch")
            chart = df.head(15).assign(segundos=df["time_ms"] / 1000)
            st.bar_chart(chart, x="swimmer_name", y="segundos", horizontal=True)

            filtros = [f"Prueba: {event[1]}", f"Piscina: {pool}", f"Género: {gender}",
                       f"Categoría: {category}", f"Liga: {league}"]
            title_lines = [
                f"Ranking — {event[1]}",
                "  ·  ".join(filtros),
                f"Rango: {rank_from.isoformat()} a {rank_to.isoformat()}  ·  "
                f"Top {len(shown)} por mejor marca",
            ]
            header = list(shown.columns)
            table = shown.astype(str).values.tolist()
            slug = "".join(c if c.isalnum() else "_" for c in event[1]).lower()[:40]

            st.markdown("**Exportar**")
            cole1, cole2 = st.columns(2)
            cole1.download_button(
                "📄 PDF", data=export.to_pdf(title_lines, header, table),
                file_name=f"ranking_{slug}.pdf", mime="application/pdf",
                width="stretch", key="rank_pdf",
            )
            cole2.download_button(
                "🖼️ Imagen PNG", data=export.to_png(title_lines, header, table),
                file_name=f"ranking_{slug}.png", mime="image/png",
                width="stretch", key="rank_png",
            )

with tab_comp:
    colf1, colf2 = st.columns(2)
    comp_category = colf1.selectbox(
        "Categoría", ["Todas"] + [label for _, label in
                                  database.get_catalog(conn, "categoria_M")],
        key="comp_cat",
        help="Categoría FECNA del año actual: año actual menos año de nacimiento",
    )
    comp_league = colf2.selectbox(
        "Liga", ["Todas"] + database.list_leagues(conn), key="comp_league",
        help="Filtra los nadadores seleccionables por liga",
    )
    colf3, colf4 = st.columns(2)
    comp_from = colf3.date_input("Desde", dt.date(2024, 1, 1), key="comp_from",
                                 help="Compara las mejores marcas dentro de este rango")
    comp_to = colf4.date_input("Hasta", dt.date.today(), key="comp_to")
    swimmers = database.list_swimmers(
        conn,
        league=None if comp_league == "Todas" else comp_league,
        age_range=(None if comp_category == "Todas"
                   else categories.age_range(comp_category)),
        reference_year=comp_to.year,
    )
    events = event_options()
    if len(swimmers) < 2 or not events:
        st.info("Se necesitan al menos dos nadadores con esos filtros; "
                "amplía la categoría o la liga.")
    else:
        col1, col2 = st.columns(2)
        swimmer_a = col1.selectbox("Nadador A", swimmers, format_func=fmt_swimmer, index=0)
        swimmer_b = col2.selectbox("Nadador B", swimmers, format_func=fmt_swimmer, index=1)
        col3, col4 = st.columns(2)
        event = col3.selectbox("Prueba", events, format_func=lambda e: e[1], key="comp_event")
        pool = col4.selectbox("Piscina", ["Todas", "LC", "SC"], key="comp_pool")
        pool_arg = None if pool == "Todas" else pool

        result = database.compare_swimmers(
            conn, swimmer_a[0], swimmer_b[0], event[0], pool_arg,
            date_from=comp_from.isoformat(), date_to=comp_to.isoformat(),
        )
        a, b = result["a"], result["b"]
        if not (a and b):
            faltan = [s[1] for s, row in ((swimmer_a, a), (swimmer_b, b)) if not row]
            st.warning(f"Sin marcas en esa prueba para: {', '.join(faltan)}")
        else:
            faster = a if a["time_ms"] <= b["time_ms"] else b
            st.success(f"Mejor marca: **{faster['swimmer_name']}** — "
                       f"diferencia de **{result['diff_ms'] / 1000:.2f} s**")
            st.dataframe(rows_to_df(
                [a, b],
                ["swimmer_name", "time_raw", "result_date", "pool_type", "club", "league"],
            ), hide_index=True, width="stretch")

            df_a = history_df(swimmer_a[0], event[0], pool_arg,
                              comp_from.isoformat(), comp_to.isoformat())
            df_b = history_df(swimmer_b[0], event[0], pool_arg,
                              comp_from.isoformat(), comp_to.isoformat())
            both = pd.concat([df_a, df_b])
            if len(both) > 2:
                st.line_chart(both, x="fecha", y="segundos", color="swimmer_name")

with tab_new:
    st.subheader("Resultados nuevos de la última sincronización")
    last = database.last_sync(conn)
    if not last:
        st.info("Aún no hay sincronizaciones. Usa 'Sincronizar todo' en la barra lateral; "
                "al terminar un campeonato, sincroniza desde su fecha de inicio para "
                "verificar los resultados que entraron.")
    else:
        st.write(f"Corrida del **{last['run_at'][:16]}** · rango {last['inicio']} → "
                 f"{last['fin']} · **{last['inserted']}** nuevos · "
                 f"{last['errors']} errores")
        new_rows = database.results_from_run(conn, last["run_at"])
        if not new_rows:
            st.success("La base ya estaba al día: ningún resultado nuevo.")
        else:
            summary = rows_to_df(database.summarize_run(conn, last["run_at"]))
            st.dataframe(summary, hide_index=True, width="stretch")
            st.dataframe(rows_to_df(
                new_rows,
                ["result_date", "time_raw", "swimmer_name", "event_name",
                 "pool_type", "gender", "club", "league"],
            ), hide_index=True, width="stretch")

with tab_evo:
    colf1, colf2 = st.columns(2)
    evo_category = colf1.selectbox(
        "Categoría", ["Todas"] + [label for _, label in
                                  database.get_catalog(conn, "categoria_M")],
        key="evo_cat",
        help="Categoría FECNA del año actual: año actual menos año de nacimiento",
    )
    evo_league = colf2.selectbox(
        "Liga", ["Todas"] + database.list_leagues(conn), key="evo_league",
        help="Filtra los nadadores seleccionables por liga",
    )
    colf3, colf4 = st.columns(2)
    evo_from = colf3.date_input("Desde", dt.date(2024, 1, 1), key="evo_from",
                                help="Acota la evolución a este rango de fechas")
    evo_to = colf4.date_input("Hasta", dt.date.today(), key="evo_to")
    swimmers = database.list_swimmers(
        conn,
        league=None if evo_league == "Todas" else evo_league,
        age_range=(None if evo_category == "Todas"
                   else categories.age_range(evo_category)),
        reference_year=evo_to.year,
    )
    if not swimmers:
        st.info("No hay nadadores con esos filtros; amplía la categoría o la liga.")
    else:
        col1, col2, col3 = st.columns(3)
        swimmer = col1.selectbox(
            "Nadador", swimmers, format_func=fmt_swimmer, key="evo_swimmer",
        )
        events = [("", "Todas")] + database.list_events(conn)
        event = col2.selectbox("Prueba", events, format_func=lambda e: e[1], key="evo_event")
        pool = col3.selectbox("Piscina", ["Todas", "LC", "SC"], key="evo_pool")

        df = history_df(
            swimmer[0], event[0] or None, None if pool == "Todas" else pool,
            evo_from.isoformat(), evo_to.isoformat(),
        )
        if df.empty:
            st.warning("Sin resultados para esos filtros.")
        else:
            st.dataframe(
                df[["result_date", "time_raw", "event_name", "pool_type", "points", "club"]],
                hide_index=True, width="stretch",
            )
            if len(df) > 1:
                st.line_chart(df, x="fecha", y="segundos", color="event_name")
            else:
                st.caption("Se necesita más de un resultado para graficar la evolución.")

with tab_swrank:
    st.subheader("Posición en el ranking del nadador, prueba por prueba")
    colr1, colr2 = st.columns(2)
    swr_league = colr1.selectbox(
        "Liga (para filtrar la lista de nadadores)",
        ["Todas"] + database.list_leagues(conn), key="swr_league_filter",
    )
    swimmers = database.list_swimmers(
        conn, league=None if swr_league == "Todas" else swr_league,
    )
    if not swimmers:
        st.info("No hay nadadores con ese filtro.")
    else:
        swimmer = colr2.selectbox(
            "Nadador", swimmers, format_func=fmt_swimmer, key="swr_swimmer",
        )
        colr3, colr4 = st.columns(2)
        swr_from = colr3.date_input("Desde", dt.date(2024, 1, 1), key="swr_from")
        swr_to = colr4.date_input("Hasta", dt.date.today(), key="swr_to")

        rows = database.swimmer_event_ranks(
            conn, swimmer[0], swr_from.isoformat(), swr_to.isoformat(),
        )
        if not rows:
            st.warning("Ese nadador no tiene marcas en el rango seleccionado.")
        else:
            event_names = sorted({r["event_name"] for r in rows})
            picked = st.multiselect(
                "Pruebas", event_names, default=event_names, key="swr_events",
                help="Deja todas o selecciona una o varias pruebas",
            )
            rows = [r for r in rows if r["event_name"] in picked]
            if not rows:
                st.info("Selecciona al menos una prueba.")
        if rows:
            league_name = next((r["league"] for r in rows if r["league"]), None)
            age = rows[0]["age"]
            st.caption(f"Liga del nadador: **{league_name or '—'}** · categoría "
                       f"**{age} años** (al {swr_to.year}). El puesto se calcula por "
                       "género y dentro de su categoría: en la liga y a nivel "
                       "nacional (Colombia).")
            df = pd.DataFrame([{
                "Prueba": r["event_name"],
                "Piscina": r["pool_type"],
                "Género": r["gender"],
                "Categoría": f"{r['age']} años",
                "Mejor marca": ms_to_time(r["best_ms"]),
                "Puesto liga": (f"{r['league_rank']} / {r['league_total']}"
                                if r["league"] else "—"),
                "Puesto Colombia": f"{r['national_rank']} / {r['national_total']}",
            } for r in rows])
            st.dataframe(df, hide_index=True, width="stretch")

            title_lines = [
                f"Rankings de {swimmer[1]} ({mask_id(swimmer[0]) if PUBLIC else swimmer[0]})",
                f"Liga: {league_name or '—'}  ·  Categoría: {age} años (al {swr_to.year})",
                f"Rango: {swr_from.isoformat()} a {swr_to.isoformat()}  ·  "
                "Puesto por género y categoría (liga / Colombia)",
            ]
            header = list(df.columns)
            table = df.astype(str).values.tolist()
            slug = "".join(c if c.isalnum() else "_" for c in swimmer[1]).lower()

            st.markdown("**Exportar**")
            cold1, cold2 = st.columns(2)
            cold1.download_button(
                "📄 PDF", data=export.to_pdf(title_lines, header, table),
                file_name=f"rankings_{slug}.pdf", mime="application/pdf",
                width="stretch",
            )
            cold2.download_button(
                "🖼️ Imagen PNG", data=export.to_png(title_lines, header, table),
                file_name=f"rankings_{slug}.png", mime="image/png",
                width="stretch",
            )
