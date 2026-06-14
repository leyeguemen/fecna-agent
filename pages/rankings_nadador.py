"""Sección: posición del nadador en el ranking, prueba por prueba."""

import datetime as dt

import pandas as pd
import streamlit as st

from fecna_agent import export, webui
from fecna_agent import db as database
from fecna_agent.times import ms_to_time

conn = webui.page_header("Rankings del nadador", "🎖️")

st.caption("Posición en el ranking del nadador, prueba por prueba.")
colr1, colr2 = st.columns(2)
swr_league = colr1.selectbox(
    "Liga (para filtrar la lista de nadadores)",
    ["Todas"] + database.list_leagues(conn), key="swr_league_filter",
)
swimmers = database.list_swimmers_detailed(
    conn, league=None if swr_league == "Todas" else swr_league,
)
if not swimmers:
    st.info("No hay nadadores con ese filtro.")
else:
    swimmer = colr2.selectbox(
        "Nadador", swimmers, format_func=webui.fmt_swimmer, key="swr_swimmer",
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
            f"Rankings de {swimmer[1]} "
            f"({webui.mask_id(swimmer[0]) if webui.PUBLIC else swimmer[0]})",
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
