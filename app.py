"""Interfaz Streamlit del agente FECNA (app multipágina).

Ejecutar:  streamlit run app.py

El menú lateral se define aquí con `st.navigation`: una lista de páginas, cada
una en su archivo dentro de `pages/`. Para administrar el menú: agrega/quita una
línea `st.Page(...)` y su archivo (el orden de la lista es el orden del menú).
El código común está en `fecna_agent/webui.py`.
"""

# IMPORTANTE: estos ajustes deben ir ANTES de `import streamlit`. Streamlit
# importa protobuf al cargarse; si no forzamos la implementación pura de
# protobuf antes, ChromaDB falla luego con "Descriptors cannot be created
# directly". También se reemplaza sqlite por pysqlite3 (ChromaDB exige >= 3.35).
import os as _os

_os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

try:
    __import__("pysqlite3")
    import sys as _sys

    _sys.modules["sqlite3"] = _sys.modules.pop("pysqlite3")
except ImportError:
    pass

import streamlit as st

from fecna_agent import webui

# Barra lateral común (estadísticas + controles). Antes de st.navigation.
webui.bootstrap()

PAGINAS = [
    st.Page("pages/inicio.py", title="Inicio", icon="🏊", default=True),
    st.Page("pages/pregunta.py", title="Pregunta", icon="💬"),
    st.Page("pages/ranking.py", title="Ranking", icon="🏆"),
    st.Page("pages/comparar.py", title="Comparar", icon="⚖️"),
    st.Page("pages/rankings_nadador.py", title="Rankings del nadador", icon="🎖️"),
    st.Page("pages/ficha.py", title="Ficha", icon="🪪"),
    st.Page("pages/programa.py", title="Programa", icon="📋"),
    st.Page("pages/novedades.py", title="Novedades", icon="🆕"),
    # Oculta: para activarla, descomenta y crea pages/evolucion.py
    # (hay una versión lista en disabled_pages/Evolucion.py).
    # st.Page("pages/evolucion.py", title="Evolución", icon="📈"),
]

st.navigation(PAGINAS).run()
