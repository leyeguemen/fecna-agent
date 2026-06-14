"""Sección: comparar las mejores marcas de dos nadadores en una prueba."""

import datetime as dt

import pandas as pd
import streamlit as st

from fecna_agent import categories, webui
from fecna_agent import db as database

conn = webui.page_header("Comparar", "⚖️")

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
swimmers = database.list_swimmers_detailed(
    conn,
    league=None if comp_league == "Todas" else comp_league,
    age_range=(None if comp_category == "Todas"
               else categories.age_range(comp_category)),
    reference_year=comp_to.year,
)
events = webui.event_options(conn)
if len(swimmers) < 2 or not events:
    st.info("Se necesitan al menos dos nadadores con esos filtros; "
            "amplía la categoría o la liga.")
else:
    col1, col2 = st.columns(2)
    swimmer_a = col1.selectbox("Nadador A", swimmers, format_func=webui.fmt_swimmer, index=0)
    swimmer_b = col2.selectbox("Nadador B", swimmers, format_func=webui.fmt_swimmer, index=1)
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
        st.dataframe(webui.rows_to_df(
            [a, b],
            ["swimmer_name", "time_raw", "result_date", "pool_type", "club", "league"],
        ), hide_index=True, width="stretch")

        df_a = webui.history_df(conn, swimmer_a[0], event[0], pool_arg,
                                comp_from.isoformat(), comp_to.isoformat())
        df_b = webui.history_df(conn, swimmer_b[0], event[0], pool_arg,
                                comp_from.isoformat(), comp_to.isoformat())
        both = pd.concat([df_a, df_b])
        if len(both) > 2:
            st.line_chart(both, x="fecha", y="segundos", color="swimmer_name")
