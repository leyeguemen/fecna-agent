"""Sección: Mis alertas.

Vista de seguimiento: muestra solo las pruebas de los nadadores que marcaste
para seguir (en la pestaña 📋 Programa), ordenadas por hora, resaltando la
próxima y cuánto falta para que empiece.
"""

from datetime import datetime
from html import escape

import streamlit as st

from fecna_agent import webui  # primero: aplica el parche sqlite/protobuf
from fecna_agent import db as database
from fecna_agent.times import ms_to_time

conn = webui.page_header("Mis alertas", "🔔")

st.caption("Pruebas de los nadadores que sigues. Marca a quién seguir en la pestaña 📋 Programa.")

_ALERTS_CSS = """
<style>
.notif-shell {
  max-width: 620px;
  margin: 0 auto 2rem;
  background: #242424;
  color: #f4f4f4;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 18px 48px rgba(0,0,0,.28);
}
.notif-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid #3d3d3d;
}
.notif-title {
  font-size: 17px;
  font-weight: 750;
}
.notif-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #e6e6e6;
  font-size: 22px;
  line-height: 1;
}
.notif-menu { letter-spacing: 2px; transform: rotate(90deg); }
.notif-section {
  padding: 14px 18px 8px;
  font-size: 15px;
  font-weight: 750;
  color: #ffffff;
}
.notif-item {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) 108px 18px;
  gap: 16px;
  align-items: start;
  padding: 12px 18px 18px;
  border-bottom: 1px solid #3d3d3d;
}
.notif-item:last-child { border-bottom: 0; }
.notif-next {
  background: linear-gradient(90deg, rgba(23,118,255,.20), rgba(36,36,36,0) 58%);
}
.notif-avatar {
  width: 48px;
  height: 48px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 21px;
  font-weight: 800;
  color: #fff;
  background: radial-gradient(circle at 35% 25%, #2dd4bf, #2563eb 55%, #111827);
  box-shadow: inset 0 0 0 2px rgba(255,255,255,.16);
}
.notif-main { min-width: 0; }
.notif-headline {
  font-size: 14px;
  line-height: 1.35;
  font-weight: 750;
  color: #f8f8f8;
}
.notif-meta {
  margin-top: 7px;
  font-size: 12px;
  color: #b7b7b7;
}
.notif-thumb {
  min-height: 58px;
  border-radius: 4px;
  padding: 8px;
  background: linear-gradient(135deg, #123c69, #00a7a5);
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
  overflow: hidden;
}
.notif-thumb strong {
  font-size: 18px;
  line-height: 1;
}
.notif-thumb span {
  margin-top: 5px;
  font-size: 10px;
  line-height: 1.15;
  font-weight: 700;
  text-transform: uppercase;
}
.notif-kebab {
  color: #e2e2e2;
  font-size: 20px;
  line-height: 1;
}
.notif-empty {
  padding: 24px 18px 28px;
  color: #cfcfcf;
  font-size: 14px;
  line-height: 1.45;
}
.notif-foot {
  padding: 12px 18px 16px;
  color: #aaa;
  font-size: 12px;
  border-top: 1px solid #3d3d3d;
}
@media (max-width: 640px) {
  .notif-shell { max-width: 100%; }
  .notif-item {
    grid-template-columns: 42px minmax(0, 1fr) 16px;
    gap: 12px;
    padding: 12px 14px 16px;
  }
  .notif-avatar { width: 42px; height: 42px; font-size: 18px; }
  .notif-thumb { display: none; }
}
</style>
"""

competitions = database.list_competitions(conn)
if not competitions:
    st.info("Aún no hay programas cargados. Sube uno en la pestaña 📋 Programa.")
    st.stop()

labels = {f"{c['name']}  ·  {c['entradas']} inscripciones": c["id"]
          for c in competitions}
chosen = st.selectbox("Campeonato", list(labels.keys()))
comp_id = labels[chosen]
user_id = webui.current_user_id()


def _query_int(name: str) -> int | None:
    raw = st.query_params.get(name)
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


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


def _render_detail(entry) -> None:
    seed = ms_to_time(entry["seed_ms"])[3:] if entry["seed_ms"] else "—"
    st.markdown(
        """
        <style>
        .alert-detail {
          max-width: 760px;
          margin: 8px auto 28px;
          padding: 22px 24px;
          border-radius: 10px;
          background: #242424;
          color: #f6f6f6;
          border: 1px solid #3f3f3f;
          box-shadow: 0 18px 48px rgba(0,0,0,.26);
        }
        .alert-detail h2 {
          margin: 0 0 8px;
          font-size: 24px;
          line-height: 1.15;
        }
        .alert-detail .muted {
          color: #b8b8b8;
          font-size: 14px;
          margin-bottom: 18px;
        }
        .alert-detail-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
          margin-top: 18px;
        }
        .alert-detail-cell {
          padding: 12px;
          border-radius: 8px;
          background: #303030;
          border: 1px solid #414141;
        }
        .alert-detail-cell span {
          display: block;
          color: #aaa;
          font-size: 12px;
          margin-bottom: 4px;
        }
        .alert-detail-cell strong {
          display: block;
          font-size: 15px;
          color: #fff;
        }
        @media (max-width: 760px) {
          .alert-detail-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="alert-detail">
          <h2>{escape(entry['swimmer_name'])}</h2>
          <div class="muted">{escape(entry['competition_name'])}</div>
          <h3>{escape(entry['event_label'] or 'Prueba sin nombre')}</h3>
          <div class="alert-detail-grid">
            <div class="alert-detail-cell"><span>Fecha</span><strong>{escape(entry['session_date'] or '—')}</strong></div>
            <div class="alert-detail-cell"><span>Hora</span><strong>{escape(entry['start_time'] or '—')}</strong></div>
            <div class="alert-detail-cell"><span>Serie</span><strong>{escape(str(entry['heat'] or '—'))}</strong></div>
            <div class="alert-detail-cell"><span>Carril</span><strong>{escape(str(entry['lane'] or '—'))}</strong></div>
            <div class="alert-detail-cell"><span>Club</span><strong>{escape(entry['club_code'] or '—')}</strong></div>
            <div class="alert-detail-cell"><span>Categoría</span><strong>{escape(entry['category'] or '—')}</strong></div>
            <div class="alert-detail-cell"><span>Semilla</span><strong>{escape(seed)}</strong></div>
            <div class="alert-detail-cell"><span>En base FECNA</span><strong>{'Sí' if entry['swimmer_id'] else 'No'}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Volver a mis alertas", type="secondary"):
        st.session_state.pop("alert_entry_id", None)
        st.query_params.clear()
        st.rerun()


def _initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "?"
    return "".join(p[0] for p in parts[:2]).upper()


def _event_summary(r) -> str:
    event = r["event_label"] or "Prueba sin nombre"
    heat = r["heat"] if r["heat"] is not None else "—"
    lane = r["lane"] if r["lane"] is not None else "—"
    seed = ms_to_time(r["seed_ms"])[3:] if r["seed_ms"] else "n.t"
    return f"{event} · serie {heat} · carril {lane} · timempo inscrito {seed}"


def _notification_item(r, *, next_item: bool, when: str) -> str:
    status = "Próxima prueba" if next_item else "Prueba programada"
    base = " · En base FECNA" if r["swimmer_id"] else ""
    category = f" · {r['category']}" if r["category"] else ""
    club = f" · {r['club_code']}" if r["club_code"] else ""
    session = f"{r['session_date'] or 'Fecha por confirmar'} · {r['start_time'] or 'Hora por confirmar'}"
    class_name = "notif-item notif-next" if next_item else "notif-item"
    return (
        f'<div class="{class_name}">'
        f'<div class="notif-avatar">{escape(_initials(r["swimmer_name"]))}</div>'
        '<div class="notif-main">'
        '<div class="notif-headline">'
        f'<strong>{escape(r["swimmer_name"])}</strong> tiene '
        f'{escape(status.lower())}: {escape(_event_summary(r))}'
        '</div>'
        f'<div class="notif-meta">{escape(when)} · {escape(session)}'
        f'{escape(category)}{escape(club)}{escape(base)}</div>'
        '</div>'
        '<div class="notif-thumb">'
        f'<strong>{escape(str(r["start_time"] or "—"))}</strong>'
        f'<span>{escape(r["event_label"] or "Programa")}</span>'
        '</div>'
        '<div class="notif-kebab">⋮</div>'
        '</div>'
    )


def _notifications_html(rows, next_idx: int | None, now: datetime) -> str:
    important, more = [], []
    for i, r in enumerate(rows):
        dt = _entry_dt(r)
        if dt is None:
            when = "horario pendiente"
        elif dt < now:
            when = "ya pasó"
        else:
            when = _humanize((dt - now).total_seconds())
        html = _notification_item(r, next_item=i == next_idx, when=when)
        if i == next_idx:
            important.append(html)
        else:
            more.append(html)

    important_html = "".join(important) or (
        "<div class='notif-empty'>No hay pruebas próximas. Las inscripciones seguidas ya pasaron "
        "o todavía no tienen horario.</div>"
    )
    more_html = "".join(more) or (
        "<div class='notif-empty'>No hay más notificaciones para este campeonato.</div>"
    )
    return (
        _ALERTS_CSS
        + '<div class="notif-shell">'
        + '<div class="notif-top">'
        + '<div class="notif-title">Notificaciones</div>'
        + '<div class="notif-actions"><span>⚙</span><span class="notif-menu">•••</span></div>'
        + '</div>'
        + '<div class="notif-section">Importante</div>'
        + important_html
        + '<div class="notif-section">Más notificaciones</div>'
        + more_html
        + f'<div class="notif-foot">{len(rows)} prueba(s) seguida(s) · actualizado {now:%H:%M}</div>'
        + '</div>'
    )


@st.fragment(run_every=60)
def _vista_alertas(comp_id: int, user_id: int):
    """Lista de notificaciones. Se reejecuta cada 60 s para refrescar la cuenta
    regresiva y recoger nadadores recién seguidos."""
    rows = database.watched_schedule(conn, comp_id, user_id)
    if not rows:
        st.info("No sigues a ningún nadador en este campeonato. Ve a 📋 Programa y "
                "selecciónalos en «🔔 Seguir nadadores».")
        return

    now = datetime.now()
    # Índice de la próxima prueba (la más cercana que aún no empieza).
    next_idx, next_dt = None, None
    for i, r in enumerate(rows):
        dt = _entry_dt(r)
        if dt and dt >= now and (next_dt is None or dt < next_dt):
            next_idx, next_dt = i, dt

    st.html(_notifications_html(rows, next_idx, now))


entry_id = _query_int("entry_id") or st.session_state.get("alert_entry_id")
if entry_id is not None:
    entry = database.watched_entry(conn, entry_id, user_id)
    if entry:
        _render_detail(entry)
        st.stop()
    st.warning("No encontré esa prueba dentro de tus alertas.")

_vista_alertas(comp_id, user_id)
