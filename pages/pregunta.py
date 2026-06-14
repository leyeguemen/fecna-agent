"""Sección: pregunta en lenguaje natural sobre la base local."""

import streamlit as st

from fecna_agent import webui  # primero: aplica el parche sqlite/protobuf
from fecna_agent import agent, llm, semantic

conn = webui.page_header("Pregunta", "💬")

if not semantic.CHROMADB_AVAILABLE:
    st.warning("Búsqueda semántica no disponible en este entorno: usa la "
               "identificación del nadador en la pregunta (las demás secciones "
               "funcionan con normalidad).")
    if semantic.CHROMADB_IMPORT_ERROR:
        with st.expander("Detalle técnico (por qué no cargó ChromaDB)"):
            st.code(semantic.CHROMADB_IMPORT_ERROR, language=None)
question = st.text_input(
    "Pregunta",
    placeholder="Compara el nadador 1105388915 con el 1094060609 en 50 libre piscina larga",
    label_visibility="collapsed",
)

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
        st.code(webui.redact(agent.answer(conn, question, use_llm=use_llm, llm_model=model)),
                language=None)
    st.caption("Los cálculos siempre se hacen en SQL/Python sobre la base local; "
               "el LLM solo redacta y los datos calculados se muestran junto a "
               "su respuesta.")
