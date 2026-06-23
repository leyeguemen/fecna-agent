"""Código común de la interfaz Streamlit multipágina.

Cada archivo de `pages/` importa este módulo y llama a `setup_page()` al inicio:
configura la página, inyecta el CSS responsivo, abre la conexión y dibuja la
barra lateral (estadísticas + controles de extracción). Así el menú lateral lo
genera Streamlit a partir de los archivos de `pages/` y cada sección queda en su
propio archivo, fácil de administrar.
"""

# Usa la implementación pura de protobuf y reemplaza sqlite por pysqlite3 ANTES
# de importar chromadb (vía semantic). Debe ejecutarse al cargar este módulo,
# que las páginas importan antes que nada.
import os as _os

_os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

try:
    __import__("pysqlite3")
    import sys

    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import base64
import datetime as dt
import hashlib
import os
import re

import pandas as pd
import streamlit as st

from fecna_agent import catalog as catalog_mod
from fecna_agent import db as database
from fecna_agent import extractor, normalizer, semantic

PAGE_ICON = "🏊"

# --- Responsivo: en pantallas angostas (móvil) las columnas se apilan en lugar
# de comprimirse y se reducen los márgenes para aprovechar el ancho. ---
_RESPONSIVE_CSS = """
<style>
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding: 1rem 0.8rem 3rem; }
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 0.5rem; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 100% !important;
  }
  h1 { font-size: 1.6rem !important; }
}
</style>
"""

_ID_RE = re.compile(r"\b\d{6,12}\b")


# --- Modo público: anonimiza identificación y fecha de nacimiento ---
def _public_mode() -> bool:
    if os.environ.get("FECNA_PUBLIC"):
        return True
    try:
        return bool(st.secrets.get("FECNA_PUBLIC", False))
    except Exception:
        return False


PUBLIC = _public_mode()


def _auth_mode() -> bool:
    if os.environ.get("FECNA_AUTH"):
        return True
    try:
        return bool(st.secrets.get("FECNA_AUTH", False))
    except Exception:
        return False


AUTH = _auth_mode()


def admin_emails() -> list[str]:
    raw = os.environ.get("FECNA_ADMIN_EMAIL")
    if not raw:
        try:
            raw = st.secrets.get("FECNA_ADMIN_EMAIL", "")
        except Exception:
            raw = ""
    from . import auth
    return auth.parse_admin_emails(raw)


def current_user():
    """Usuario en sesión (dict) o None."""
    return st.session_state.get("auth_user")


def is_admin() -> bool:
    """Sin candado, acceso total (modo local). Con candado, solo rol admin."""
    if not AUTH:
        return True
    user = current_user()
    return bool(user and user.get("role") == "admin")


def logout() -> None:
    st.session_state.pop("auth_user", None)
    st.rerun()


def render_login_register(conn) -> None:
    """Formularios de inicio de sesión y registro (pestañas)."""
    from . import auth, db as database

    st.title("🔐 Acceso")
    tab_login, tab_reg = st.tabs(["Iniciar sesión", "Registrarse"])

    with tab_login:
        with st.form("login"):
            email = st.text_input("Email")
            pwd = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                user = database.authenticate(conn, email, pwd)
                if user:
                    st.session_state["auth_user"] = dict(user)
                    st.rerun()
                else:
                    st.error("Email o contraseña incorrectos.")

    with tab_reg:
        with st.form("registro"):
            email = st.text_input("Email", key="reg_email")
            pwd = st.text_input("Contraseña", type="password", key="reg_pwd")
            pwd2 = st.text_input("Repite la contraseña", type="password", key="reg_pwd2")
            if st.form_submit_button("Crear cuenta", type="primary"):
                if pwd != pwd2:
                    st.error("Las contraseñas no coinciden.")
                else:
                    try:
                        role = auth.role_for(email, admin_emails())
                        user = database.create_user(conn, email, pwd, role=role)
                        st.session_state["auth_user"] = user
                        st.success("Cuenta creada.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))


def require_auth() -> None:
    """Si el candado está activo y no hay sesión, muestra el acceso y detiene."""
    if not AUTH or current_user():
        return
    render_login_register(get_conn())
    st.stop()


def mask_id(swimmer_id) -> str:
    """Código pseudónimo estable, no reversible, para distinguir homónimos."""
    digest = hashlib.sha1(str(swimmer_id).encode()).hexdigest()[:5].upper()
    return f"#{digest}"


def fmt_swimmer(s) -> str:
    """Etiqueta de un nadador para los selectores: nombre + club y liga (sin
    cédula), para identificarlo más fácil."""
    club = s[2] if len(s) > 2 else None
    league = s[3] if len(s) > 3 else None
    extra = " · ".join(x for x in (club, league) if x)
    return f"{s[1]} ({extra})" if extra else s[1]


def redact(text: str) -> str:
    """Oculta números de identificación en texto libre (modo público)."""
    return _ID_RE.sub("·····", text) if PUBLIC else text


def data_uri(uploaded) -> str | None:
    """Convierte un archivo subido (foto/logo) en un data URI para la ficha."""
    if not uploaded:
        return None
    data = uploaded.getvalue()
    mime = uploaded.type or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _resolve_db_path():
    """Base a usar: FECNA_DB si está; si no, la cruda local; y como respaldo en
    la nube (donde la cruda no se sube), la anonimizada."""
    if os.environ.get("FECNA_DB"):
        return os.environ["FECNA_DB"]
    if database.DEFAULT_DB_PATH.exists():
        return database.DEFAULT_DB_PATH
    public = database.DEFAULT_DB_PATH.parent / "fecna_public.db"
    return public if public.exists() else database.DEFAULT_DB_PATH


def get_conn():
    """Conexión nueva por ejecución (sqlite no se comparte entre hilos)."""
    return database.connect(_resolve_db_path())


@st.cache_resource
def ensure_semantic_index() -> str | None:
    """Reconstruye el índice semántico si falta (p. ej. al desplegar subiendo
    solo la base). Se ejecuta una sola vez por arranque."""
    conn = get_conn()
    try:
        client = semantic.get_client()
        if client.get_collection(semantic.EVENTS_COLLECTION).count() > 0:
            return None
    except Exception:
        pass
    if database.get_catalog(conn, "prueba") and database.list_events(conn):
        return semantic.rebuild_from_db(conn)
    return None


@st.cache_resource(show_spinner="Preparando el generador de imágenes/PDF "
                                "(solo la primera vez)…")
def ensure_browser() -> bool:
    """Garantiza el navegador de Playwright (lo instala en la nube si falta).
    Cacheado: corre una sola vez por arranque."""
    from fecna_agent import ficha

    return ficha.ensure_browser()


def rows_to_df(rows, columns=None) -> pd.DataFrame:
    df = pd.DataFrame([dict(row) for row in rows])
    return df[columns] if columns is not None and not df.empty else df


def event_options(conn, prefer_local: bool = True) -> list[tuple[str, str]]:
    """Pruebas para los selects: las que tienen datos locales, o el catálogo."""
    local = database.list_events(conn) if prefer_local else []
    return local or database.get_catalog(conn, "prueba")


def rebuild_index(conn) -> str:
    return semantic.rebuild_from_db(conn)


def history_df(conn, swimmer_id, event_id, pool, date_from=None, date_to=None):
    rows = database.history(conn, swimmer_id, event_id, pool, date_from, date_to)
    df = rows_to_df(rows)
    if not df.empty:
        df["segundos"] = df["time_ms"] / 1000
        df["fecha"] = pd.to_datetime(df["result_date"])
    return df


def admin_controls(conn):
    """Controles de extracción/sincronización. Ocultos en modo público para que
    la app desplegada sea de solo lectura."""
    st.subheader("Extraer desde FECNA")

    catalog_events = database.get_catalog(conn, "prueba")
    if not catalog_events:
        st.info("Sin catálogo de pruebas: descárgalo abajo.")
    event_pick = st.selectbox(
        "Prueba", catalog_events, format_func=lambda e: e[1], key="fetch_event",
    ) if catalog_events else None

    pool_pick = st.selectbox("Piscina", ["LC", "SC"], key="fetch_pool")
    gender_pick = st.selectbox("Género", ["M", "F"], key="fetch_gender")
    category_pick = st.text_input("Categoría (ej. 12 AÑOS, vacío = todas)", key="fetch_cat")
    date_from = st.date_input("Desde", dt.date(2024, 1, 1), key="fetch_from")
    date_to = st.date_input("Hasta", dt.date.today(), key="fetch_to")

    if st.button("Extraer y guardar", disabled=event_pick is None):
        with st.spinner("Consultando FECNA..."):
            try:
                raw = extractor.fetch_ranking(
                    inicio=date_from.isoformat(), fin=date_to.isoformat(),
                    genero=gender_pick, categoria=category_pick,
                    prueba=event_pick[0], piscina=pool_pick,
                )
                inserted = database.insert_results(conn, normalizer.normalize_rows(raw))
                st.success(f"{len(raw)} recibidos, {inserted} nuevos guardados.")
                st.info(rebuild_index(conn))
            except Exception as exc:
                st.error(f"Error de extracción: {exc}")

    st.divider()
    st.subheader("Sincronización masiva")
    sync_from = st.date_input("Sincronizar desde", dt.date(2024, 1, 1), key="sync_from",
                              help="Para verificar un campeonato, usa su fecha de inicio")
    if st.button("Sincronizar todo (pruebas × piscinas × géneros)"):
        from fecna_agent import sync as sync_mod

        bar = st.progress(0.0, text="Sincronizando...")

        def on_progress(done, total, detail):
            event_name, pool, gender, received, inserted, error = detail
            bar.progress(done / total, text=f"{event_name} {pool} {gender} "
                                            f"({done}/{total})")

        try:
            stats = sync_mod.sync_all(conn, inicio=sync_from.isoformat(),
                                      progress=on_progress)
            bar.empty()
            if stats["aborted"]:
                st.error(f"Sincronización abortada: {stats['aborted']}")
            else:
                st.success(f"{stats['received']} recibidos, {stats['inserted']} nuevos, "
                           f"{stats['errors']} errores.")
            if stats["inserted"]:
                st.info(rebuild_index(conn))
        except Exception as exc:
            bar.empty()
            st.error(f"Error de sincronización: {exc}")

    last = database.last_sync(conn)
    if last:
        st.caption(f"Última sincronización: {last['run_at'][:16]} · "
                   f"{last['inserted']} nuevos · {last['errors']} errores")

    st.divider()
    if st.button("Descargar catálogos"):
        with st.spinner("Descargando catálogos..."):
            saved = database.save_catalogs(conn, catalog_mod.fetch_catalogs())
            st.success(f"{saved} entradas de catálogo guardadas.")
    if st.button("Reconstruir índice semántico"):
        st.success(rebuild_index(conn))


def bootstrap():
    """Configura la página, inyecta el CSS responsivo y dibuja la barra lateral
    común (estadísticas + controles). Se llama UNA vez en `app.py`, antes de
    `st.navigation`, así la barra lateral aparece en todas las páginas."""
    st.set_page_config(page_title="FECNA Natación", page_icon=PAGE_ICON,
                       layout="wide", initial_sidebar_state="expanded")
    st.markdown(_RESPONSIVE_CSS, unsafe_allow_html=True)

    conn = get_conn()
    ensure_semantic_index()

    with st.sidebar:
        user = current_user()
        if AUTH and user:
            st.caption(f"👤 {user['email']}")
            if st.button("Cerrar sesión"):
                logout()
        if not PUBLIC and is_admin():
            admin_controls(conn)


def page_header(title: str, icon: str = PAGE_ICON):
    """Encabezado de una página y conexión a la base. Lo llama cada archivo de
    `pages/` al inicio."""
    st.title(f"{icon} {title}")
    return get_conn()
