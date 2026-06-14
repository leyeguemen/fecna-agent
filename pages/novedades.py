"""Sección: resultados nuevos de la última sincronización."""

import streamlit as st

from fecna_agent import webui
from fecna_agent import db as database

conn = webui.page_header("Novedades", "🆕")

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
        summary = webui.rows_to_df(database.summarize_run(conn, last["run_at"]))
        st.dataframe(summary, hide_index=True, width="stretch")
        st.dataframe(webui.rows_to_df(
            new_rows,
            ["result_date", "time_raw", "swimmer_name", "event_name",
             "pool_type", "gender", "club", "league"],
        ), hide_index=True, width="stretch")
