"""Sección: Mis alertas.

Vista de seguimiento: muestra solo las pruebas de los nadadores que marcaste
para seguir (en la pestaña 📋 Programa), ordenadas por hora, resaltando la
próxima y cuánto falta para que empiece.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from fecna_agent import webui  # primero: aplica el parche sqlite/protobuf
from fecna_agent import db as database
from fecna_agent.times import ms_to_time

conn = webui.page_header("Mis alertas", "🔔")

st.caption("Pruebas de los nadadores que sigues, ordenadas por hora. La próxima "
           "queda resaltada. Marca a quién seguir en la pestaña 📋 Programa.")

competitions = database.list_competitions(conn)
if not competitions:
    st.info("Aún no hay programas cargados. Sube uno en la pestaña 📋 Programa.")
    st.stop()

labels = {f"{c['name']}  ·  {c['entradas']} inscripciones": c["id"]
          for c in competitions}
chosen = st.selectbox("Campeonato", list(labels.keys()))
comp_id = labels[chosen]


def _entry_dt(r):
    """Combina fecha + hora de la inscripción en un datetime (o None)."""
    if not r["session_date"] or not r["start_time"]:
        return None
    try:
        return datetime.fromisoformat(f"{r['session_date']}T{r['start_time']}")
    except ValueError:
        return None


def _humanize(seconds: float) -> str:
    mins = int(seconds // 60)
    if mins < 60:
        return f"faltan {mins} min"
    horas, mins = divmod(mins, 60)
    if horas < 24:
        return f"faltan {horas} h {mins} min"
    return f"faltan {horas // 24} d"


@st.fragment(run_every=60)
def _vista_alertas(comp_id: int):
    """Banner + tabla. Se reejecuta solo cada 60 s para refrescar la cuenta
    regresiva y recoger nadadores recién seguidos, sin recargar la página."""
    rows = database.watched_schedule(conn, comp_id)
    if not rows:
        st.info("No sigues a ningún nadador en este campeonato. Ve a 📋 Programa y "
                "selecciónalos en «🔔 Seguir nadadores».")
        return

    now = datetime.now()
    st.caption(f"Actualizado {now:%H:%M} · se refresca cada minuto.")
    # Índice de la próxima prueba (la más cercana que aún no empieza).
    next_idx, next_dt = None, None
    for i, r in enumerate(rows):
        dt = _entry_dt(r)
        if dt and dt >= now and (next_dt is None or dt < next_dt):
            next_idx, next_dt = i, dt

    if next_idx is not None:
        nr = rows[next_idx]
        st.success(f"⏰ Próxima: **{nr['swimmer_name']}** · {nr['event_label']} · "
                   f"serie {nr['heat']} carril {nr['lane']} · {nr['start_time']} "
                   f"({_humanize((next_dt - now).total_seconds())})")
    else:
        st.info("No hay pruebas próximas: todas las inscripciones seguidas ya pasaron.")

    records = []
    for i, r in enumerate(rows):
        dt = _entry_dt(r)
        if dt is None:
            cuando = "—"
        elif dt < now:
            cuando = "ya pasó"
        else:
            cuando = _humanize((dt - now).total_seconds())
        seed = ms_to_time(r["seed_ms"])[3:] if r["seed_ms"] else "—"
        records.append({
            "": "⏰" if i == next_idx else "",
            "Fecha": r["session_date"] or "—",
            "Hora": r["start_time"] or "—",
            "Nadador": r["swimmer_name"],
            "Prueba": r["event_label"] or "—",
            "Cat.": r["category"],
            "Serie": r["heat"] or "—",
            "Carril": r["lane"],
            "Club": r["club_code"],
            "Semilla": seed,
            "En base": "✅" if r["swimmer_id"] else "",
            "Cuándo": cuando,
        })

    def _resaltar(row):
        es_proxima = next_idx is not None and row.name == next_idx
        return ["background-color: #fff3cd" if es_proxima else ""] * len(row)

    df = pd.DataFrame(records)
    st.dataframe(df.style.apply(_resaltar, axis=1), hide_index=True, width="stretch")
    st.caption(f"{len(rows)} prueba(s) seguida(s). «En base» ✅ = el nadador está en "
               "la base de FECNA.")


_vista_alertas(comp_id)
