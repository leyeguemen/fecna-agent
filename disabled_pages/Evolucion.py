"""Sección OCULTA: evolución de marcas de un nadador.

Para reactivarla: copia este archivo a `pages/evolucion.py` y descomenta su
línea `st.Page(...)` en `app.py`.
"""

import datetime as dt

import streamlit as st

from fecna_agent import categories, webui
from fecna_agent import db as database

conn = webui.page_header("Evolución", "📈")

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
swimmers = database.list_swimmers_detailed(
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
        "Nadador", swimmers, format_func=webui.fmt_swimmer, key="evo_swimmer",
    )
    events = [("", "Todas")] + database.list_events(conn)
    event = col2.selectbox("Prueba", events, format_func=lambda e: e[1], key="evo_event")
    pool = col3.selectbox("Piscina", ["Todas", "LC", "SC"], key="evo_pool")

    df = webui.history_df(
        conn, swimmer[0], event[0] or None, None if pool == "Todas" else pool,
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
