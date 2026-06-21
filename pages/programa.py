"""Sección: Programa del campeonato.

Carga el heat sheet (PDF) de un campeonato y muestra, por club o por nadador,
las pruebas que debe presentar y a qué hora. Cruza los nombres con la base para
enriquecer con la mejor marca de cada deportista cuando existe.
"""

import hashlib
import io

import pandas as pd
import streamlit as st

from fecna_agent import webui  # primero: aplica el parche sqlite/protobuf
from fecna_agent import db as database
from fecna_agent import programa
from fecna_agent.times import ms_to_time

conn = webui.page_header("Programa", "📋")

st.caption("Carga el programa (PDF) de un campeonato y filtra por club o nadador "
           "para ver qué pruebas debe presentar y a qué hora.")

# --- Cargar un nuevo programa -------------------------------------------------
# El PDF se parsea UNA sola vez por archivo y el resultado se guarda en
# session_state. Así sobrevive a los reruns (cada tecla del nombre o el clic en
# Guardar reejecutan el script) sin volver a leer el buffer del uploader, que
# tras la primera lectura queda al final y devolvería vacío.
def _parse_uploaded(uploaded):
    data = uploaded.getvalue()
    key = hashlib.sha1(data).hexdigest()
    if st.session_state.get("prog_key") == key:
        return  # ya parseado en esta sesión
    competition, entries = programa.parse_pdf(io.BytesIO(data))
    if entries:
        programa.map_event_ids(entries, database.event_index(conn))
        stats = programa.match_swimmers(entries, database.list_swimmers(conn))
    else:
        stats = {"matched": 0, "ambiguous": 0, "total": 0}
    st.session_state.update(prog_key=key, prog_comp=competition,
                            prog_entries=entries, prog_stats=stats)


with st.expander("➕ Cargar un nuevo programa (PDF)", expanded=False):
    uploaded = st.file_uploader("Programa del campeonato (PDF)", type=["pdf"])
    if uploaded is not None:
        try:
            _parse_uploaded(uploaded)
        except ModuleNotFoundError:
            st.error("Falta la dependencia `pdfplumber`. Instálala: "
                     "pip install pdfplumber")
            st.stop()
        except Exception as exc:
            st.error(f"No pude leer el PDF: {exc}")
            st.stop()

        competition = st.session_state["prog_comp"]
        entries = st.session_state["prog_entries"]
        stats = st.session_state["prog_stats"]
        if not entries:
            st.warning("No se reconocieron inscripciones en el PDF. "
                       "¿Es un programa con texto (no escaneado)?")
        else:
            st.success(f"{len(entries)} inscripciones · "
                       f"{stats['matched']} nadadores cruzados con la base"
                       + (f" · {stats['ambiguous']} homónimos sin cruzar"
                          if stats["ambiguous"] else ""))
            name = st.text_input("Nombre del campeonato",
                                 value=competition.get("name") or "")
            pool = st.selectbox(
                "Piscina", ["LC", "SC"],
                index=0 if (competition.get("pool_type") or "LC") == "LC" else 1,
            )
            if st.button("💾 Guardar programa", type="primary", disabled=not name):
                competition["name"] = name
                competition["pool_type"] = pool
                result = database.save_competition(conn, competition, entries)
                msg = {
                    "created": "Programa guardado.",
                    "updated": "Había cambios: programa actualizado.",
                    "unchanged": "Sin cambios: la programación ya estaba al día.",
                }[result["status"]]
                if result["status"] == "unchanged":
                    st.info(msg)
                else:
                    # Limpia el parseo cacheado y refresca para mostrarlo guardado.
                    for k in ("prog_key", "prog_comp", "prog_entries", "prog_stats"):
                        st.session_state.pop(k, None)
                    st.success(msg)
                    st.rerun()

# --- Seleccionar un programa guardado -----------------------------------------
competitions = database.list_competitions(conn)
if not competitions:
    st.info("Aún no hay programas cargados. Usa el panel de arriba para subir uno.")
    st.stop()

labels = {f"{c['name']}  ·  {c['entradas']} inscripciones": c["id"]
          for c in competitions}
chosen = st.selectbox("Campeonato", list(labels.keys()))
comp_id = labels[chosen]

# --- Seguir nadadores (alertas) ----------------------------------------------
all_swimmers = database.competition_swimmers(conn, comp_id)
name_to_label = {n: f"{n} ({c})" for n, c in all_swimmers}
label_to_name = {v: k for k, v in name_to_label.items()}
watched = database.list_watched(conn, comp_id)
picked = st.multiselect(
    "🔔 Seguir nadadores",
    options=list(label_to_name.keys()),
    default=[name_to_label[n] for n in watched if n in name_to_label],
    help="Los seguidos aparecen en la pestaña 🔔 Alertas con su próxima prueba y "
         "cuenta regresiva.",
)
picked_names = sorted(label_to_name[lbl] for lbl in picked)
if picked_names != sorted(watched):
    database.set_watched(conn, comp_id, picked_names)
    st.rerun()

col_a, col_b, col_c = st.columns([3, 3, 1])
clubs = ["— Todos —"] + database.competition_clubs(conn, comp_id)
club_pick = col_a.selectbox("Club (código del PDF)", clubs)
club = None if club_pick == "— Todos —" else club_pick

swimmers = database.competition_swimmers(conn, comp_id)
if club:
    swimmers = [(n, c) for n, c in swimmers if c == club]
swim_labels = {"— Todos —": None} | {f"{n} ({c})": n for n, c in swimmers}
swim_pick = col_b.selectbox("Nadador", list(swim_labels.keys()))
swimmer = swim_labels[swim_pick]

if not webui.PUBLIC and col_c.button("🗑️", help="Eliminar este programa"):
    database.delete_competition(conn, comp_id)
    st.rerun()

# --- Cronograma ---------------------------------------------------------------
rows = database.competition_schedule(conn, comp_id, club, swimmer)
if not rows:
    st.warning("Sin inscripciones para ese filtro.")
    st.stop()

records = []
for r in rows:
    seed = ms_to_time(r["seed_ms"])[3:] if r["seed_ms"] else "—"
    records.append({
        "Fecha": r["session_date"] or "—",
        "Jornada": r["session_no"] if r["session_no"] is not None else "—",
        "Hora": r["start_time"] or "—",
        "Nº": r["event_number"],
        "Prueba": r["event_label"] or "—",
        "Cat.": r["category"],
        "Serie": r["heat"] or "—",
        "Carril": r["lane"],
        "Nadador": r["swimmer_name"],
        "Club": r["club_code"],
        "Semilla": seed,
        "En base": "✅" if r["swimmer_id"] else "",
    })
df = pd.DataFrame(records)
st.dataframe(df, hide_index=True, width="stretch")

st.caption(f"{len(rows)} prueba(s). «En base» ✅ = el nadador está en la base de "
           "FECNA (puedes ver su mejor marca y ranking en las otras secciones).")
