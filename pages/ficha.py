"""Sección: ficha visual del nadador con sus mejores pruebas."""

import datetime as dt

import streamlit as st
import streamlit.components.v1 as components

from fecna_agent import ficha, webui
from fecna_agent import db as database


@st.cache_data(show_spinner=False)
def _ficha_png(html: str) -> bytes:
    return ficha.render_png(html)


@st.cache_data(show_spinner=False)
def _ficha_pdf(html: str) -> bytes:
    return ficha.render_pdf(html)


conn = webui.page_header("Ficha", "🪪")

colf1, colf2 = st.columns(2)
fic_league = colf1.selectbox(
    "Liga (para filtrar la lista de nadadores)",
    ["Todas"] + database.list_leagues(conn), key="fic_league_filter",
)
fic_swimmers = database.list_swimmers_detailed(
    conn, league=None if fic_league == "Todas" else fic_league,
)
if not fic_swimmers:
    st.info("No hay nadadores con ese filtro.")
else:
    fic_swimmer = colf2.selectbox(
        "Nadador", fic_swimmers, format_func=webui.fmt_swimmer, key="fic_swimmer",
    )
    colf3, colf4, colf5 = st.columns(3)
    fic_pool = colf3.selectbox("Piscina", ["Ambas", "LC", "SC"], key="fic_pool")
    fic_from = colf4.date_input("Desde", dt.date(2024, 1, 1), key="fic_from")
    fic_to = colf5.date_input("Hasta", dt.date.today(), key="fic_to")

    profile = database.swimmer_profile(
        conn, fic_swimmer[0],
        pool_type=None if fic_pool == "Ambas" else fic_pool,
        date_from=fic_from.isoformat(), date_to=fic_to.isoformat(),
    )
    if not profile:
        st.warning("Ese nadador no tiene marcas en el rango seleccionado.")
    elif not profile["top_events"]:
        st.info("No tiene pruebas en la piscina seleccionada.")
    else:
        st.markdown("**Personalizar la ficha** (opcional)")
        cola, colb = st.columns(2)
        fic_photo = cola.file_uploader("Foto del nadador",
                                       type=["png", "jpg", "jpeg"], key="fic_photo")
        fic_logo = colb.file_uploader("Logo del club",
                                      type=["png", "jpg", "jpeg"], key="fic_logo")
        colc, cold = st.columns(2)
        fic_champ = colc.text_input("Campeonato",
                                    placeholder="CAMPEONATO NACIONAL INTERCLUBES 2026",
                                    key="fic_champ")
        fic_venue = cold.text_input("Sede", placeholder="IBAGUÉ", key="fic_venue")

        html = ficha.render_html(
            profile,
            photo_data_uri=webui.data_uri(fic_photo),
            logo_data_uri=webui.data_uri(fic_logo),
            championship=fic_champ or None,
            venue=fic_venue or None,
        )
        components.html(html, height=1180, scrolling=True)

        slug = "".join(c if c.isalnum() else "_"
                       for c in profile["swimmer_name"]).lower()
        st.markdown("**Descargar**")
        render_error = None
        png = pdf = None
        if webui.ensure_browser():
            try:
                with st.spinner("Generando imagen y PDF..."):
                    png = _ficha_png(html)
                    pdf = _ficha_pdf(html)
            except Exception as exc:
                render_error = exc

        if png and pdf:
            c1, c2, c3 = st.columns(3)
            c1.download_button(
                "🖼️ PNG (redes)", data=png, file_name=f"ficha_{slug}.png",
                mime="image/png", width="stretch",
                help="Imagen lista para publicar en redes sociales.",
            )
            c2.download_button(
                "📄 PDF (imprimir)", data=pdf, file_name=f"ficha_{slug}.pdf",
                mime="application/pdf", width="stretch",
                help="Una página del tamaño de la ficha, lista para imprimir.",
            )
            c3.download_button(
                "🌐 HTML", data=html.encode("utf-8"), file_name=f"ficha_{slug}.html",
                mime="text/html", width="stretch",
                help="Versión editable; ábrela en el navegador.",
            )
        else:
            st.warning("El generador de PNG/PDF no está disponible en este entorno. "
                       "Descarga el HTML y conviértelo desde el navegador "
                       "(Imprimir → Guardar como PDF, o captura para imagen).")
            st.download_button(
                "🌐 Descargar ficha (HTML)", data=html.encode("utf-8"),
                file_name=f"ficha_{slug}.html", mime="text/html", width="stretch",
            )
            if render_error:
                st.caption(f"Detalle técnico: {render_error}")
