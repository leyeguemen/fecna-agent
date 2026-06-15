"""Sección: chatbot para trabajar con la data en lenguaje natural."""

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

st.caption("Pregunta sobre la data: mejor marca, ranking, comparar o evolución. "
           "Recuerda el contexto, así que puedes seguir con 'y su evolución?' o "
           "'compáralo con 1094060609'. Los cálculos siempre son SQL/Python.")

# --- Estado del chat ---
if "chat_msgs" not in st.session_state:
    st.session_state.chat_msgs = []
if "chat_ctx" not in st.session_state:
    st.session_state.chat_ctx = {}

# --- Controles: redacción con IA local y limpiar ---
ollama_up = llm.is_available()
col1, col2, col3 = st.columns([2, 2, 1])
use_llm = col1.toggle(
    "Redactar con IA local", value=False, disabled=not ollama_up,
    help="Usa Ollama para redactar; los cálculos siguen siendo SQL/Python.",
)
model = None
if ollama_up and use_llm:
    model = col2.selectbox("Modelo", llm.list_models(), label_visibility="collapsed")
elif not ollama_up:
    col2.caption("Ollama no está corriendo: respuestas determinísticas.")
if col3.button("🗑️ Limpiar", width="stretch"):
    st.session_state.chat_msgs = []
    st.session_state.chat_ctx = {}
    st.rerun()


def _render(role: str, content: str):
    with st.chat_message(role):
        if role == "user":
            st.markdown(content)
        else:
            st.code(webui.redact(content), language=None)


# --- Historial ---
for m in st.session_state.chat_msgs:
    _render(m["role"], m["content"])

# --- Entrada ---
prompt = st.chat_input("Escribe tu pregunta sobre la data…")
if prompt:
    _render("user", prompt)
    with st.chat_message("assistant"):
        with st.spinner("Consultando..."):
            reply, st.session_state.chat_ctx = agent.chat_answer(
                conn, prompt, context=st.session_state.chat_ctx,
                use_llm=use_llm, llm_model=model,
            )
        st.code(webui.redact(reply), language=None)
    st.session_state.chat_msgs.append({"role": "user", "content": prompt})
    st.session_state.chat_msgs.append({"role": "assistant", "content": reply})
