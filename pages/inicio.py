"""Página de inicio: resumen con métricas de la base."""

import streamlit as st

from fecna_agent import webui
from fecna_agent import db as database

conn = webui.page_header("Inicio")

st.markdown("Consulta y compara resultados de natación de los reportes públicos "
            "de FECNA. Elige una sección en el menú lateral.")

total = conn.execute("SELECT COUNT(*) FROM ranking_results").fetchone()[0]
swimmers = len(database.list_swimmers(conn))
events = len(database.list_events(conn))
leagues = len(database.list_leagues(conn))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Resultados", f"{total:,}")
c2.metric("Nadadores", f"{swimmers:,}")
c3.metric("Pruebas con datos", events)
c4.metric("Ligas", leagues)

st.divider()
st.subheader("Secciones")
st.markdown(
    "- **💬 Pregunta** — pregunta en lenguaje natural sobre la base local.\n"
    "- **🏆 Ranking** — ranking por prueba, categoría, liga y rango de fechas.\n"
    "- **⚖️ Comparar** — compara las mejores marcas de dos nadadores.\n"
    "- **🎖️ Rankings del nadador** — puesto por prueba, en su liga y nacional.\n"
    "- **🪪 Ficha** — ficha visual del nadador con sus mejores pruebas.\n"
    "- **🆕 Novedades** — resultados nuevos de la última sincronización."
)
