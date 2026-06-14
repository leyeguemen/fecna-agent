"""Sección: ranking por mejor marca, con filtros de prueba/categoría/liga/fecha."""

import datetime as dt

import streamlit as st

from fecna_agent import categories, export, webui
from fecna_agent import db as database
from fecna_agent.times import ms_to_time

conn = webui.page_header("Ranking", "🏆")

events = webui.event_options(conn)
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
        df = webui.rows_to_df(rows)
        df.insert(0, "puesto", range(1, len(df) + 1))
        df["tiempo"] = df["time_ms"].map(ms_to_time)
        cols = ["puesto", "tiempo", "swimmer_name", "birth_date", "club",
                "league", "result_date"]
        if webui.PUBLIC:
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
