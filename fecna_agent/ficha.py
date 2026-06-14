"""Ficha visual del nadador: infografía HTML auto-contenida.

Recibe el perfil que arma `db.swimmer_profile` (datos personales + mejores
pruebas por puesto nacional) y produce un HTML con CSS embebido y, si se
proporcionan, la foto y el logo como data URIs. No depende de Streamlit ni de
la base: es fácil de probar y de renderizar/imprimir en cualquier navegador.
"""

from html import escape
from string import Template

from .times import ms_to_time

# Niveles para la insignia "TOP X DE COLOMBIA".
_TIERS = (3, 5, 10, 20, 50)


def pretty_time(ms: int) -> str:
    """28840 → '28.84', 67510 → '1:07.51', 183320 → '3:03.32' (sin ceros a la izq.)."""
    hours, minutes, rest = ms_to_time(ms).split(":")
    if hours != "00":
        return f"{int(hours)}:{minutes}:{rest}"
    if minutes != "00":
        return f"{int(minutes)}:{rest}"
    return rest


def short_event(event_name: str) -> str:
    """'200m Mariposa/200m Fly' → '200m Mariposa' (se queda con el nombre en español)."""
    return event_name.split("/")[0].strip()


def _tier(rank: int) -> int:
    for t in _TIERS:
        if rank <= t:
            return t
    return ((rank + 9) // 10) * 10


def derive_highlights(profile: dict) -> dict:
    """Calcula los destacados de la imagen: mejor puesto nacional y podios de liga."""
    top = list(profile["top_events"])
    best = min(top, key=lambda r: r["national_rank"]) if top else None
    return {
        "best_national": best,
        "national_tier": _tier(best["national_rank"]) if best else None,
        "national_top10": [r for r in top if r["national_rank"] <= 10],
        "league_gold": [r for r in top if r["league_rank"] == 1],
        "league_silver": [r for r in top if r["league_rank"] == 2],
        "league_bronze": [r for r in top if r["league_rank"] == 3],
    }


def _medal(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "")


def _pos(rank: int, total: int) -> str:
    medal = _medal(rank)
    medal = f"{medal} " if medal else ""
    return f"{medal}{rank}.º <span class='of'>de {total}</span>"


def _rows_html(top: list) -> str:
    rows = []
    for r in top:
        liga = (_pos(r["league_rank"], r["league_total"])
                if r["league"] and r["league_rank"] else "<span class='of'>—</span>")
        rows.append(
            "<tr>"
            f"<td class='ev'>{escape(short_event(r['event_name']))}"
            f"<span class='pool'>{escape(r['pool_type'])}</span></td>"
            f"<td class='time'>{pretty_time(r['best_ms'])}</td>"
            f"<td>{liga}</td>"
            f"<td>{_pos(r['national_rank'], r['national_total'])}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _highlights_html(profile: dict, h: dict) -> str:
    blocks = []
    best = h["best_national"]
    if best:
        champ = best["national_rank"] == 1
        label = "CAMPEÓN DE COLOMBIA" if champ else f"TOP {h['national_tier']} DE COLOMBIA"
        blocks.append(
            "<div class='hl hl-gold'>"
            "<div class='hl-medal'>🥇</div>"
            f"<div class='hl-title'>{label}</div>"
            f"<div class='hl-detail'><b>{escape(short_event(best['event_name']))}</b>"
            f"<span>{pretty_time(best['best_ms'])}</span>"
            f"<span class='hl-pos'>{best['national_rank']}.º de {best['national_total']} nacional</span>"
            "</div></div>"
        )
    podio = h["league_gold"] or h["league_silver"] or h["league_bronze"]
    if podio:
        medal_kind, events = (
            ("🥇 CAMPEÓN", h["league_gold"]) if h["league_gold"] else
            ("🥈 SUBCAMPEÓN", h["league_silver"]) if h["league_silver"] else
            ("🥉 TERCERO", h["league_bronze"])
        )
        chips = "".join(
            f"<div class='chip'><b>{escape(short_event(e['event_name']))}</b>"
            f"<span>{pretty_time(e['best_ms'])}</span>"
            f"<span class='hl-pos'>{e['league_rank']}.º de {e['league_total']}</span></div>"
            for e in events
        )
        liga = escape(profile["league"] or "")
        blocks.append(
            "<div class='hl hl-silver'>"
            f"<div class='hl-title'>{medal_kind} LIGA {liga}</div>"
            f"<div class='chips'>{chips}</div></div>"
        )
    return "\n".join(blocks)


def render_html(
    profile: dict,
    *,
    photo_data_uri: str | None = None,
    logo_data_uri: str | None = None,
    championship: str | None = None,
    venue: str | None = None,
) -> str:
    """Devuelve el HTML completo y auto-contenido de la ficha."""
    h = derive_highlights(profile)
    name = escape(profile["swimmer_name"])
    parts = name.split()
    first = escape(parts[0]) if parts else name
    rest = escape(" ".join(parts[1:])) if len(parts) > 1 else ""
    club = escape(profile["club"] or "—")
    league = escape(profile["league"] or "—")
    gender = {"M": "Masculino", "F": "Femenino"}.get(profile["gender"], profile["gender"] or "")

    photo = (f"<img class='photo' src='{photo_data_uri}' alt='foto'>"
             if photo_data_uri else "")
    logo = (f"<img class='logo' src='{logo_data_uri}' alt='logo'>"
            if logo_data_uri else "")
    champ_line = escape(championship) if championship else ""
    venue_line = escape(venue) if venue else ""
    champ_html = (
        f"<div class='champ'><div class='champ-name'>{champ_line}</div>"
        f"<div class='champ-venue'>{venue_line}</div></div>"
    ) if champ_line or venue_line else ""

    quote = (f"El esfuerzo de cada entrenamiento se refleja en los resultados. "
             f"<b>{first} {rest}</b> continúa posicionándose entre los mejores "
             f"nadadores de Colombia en la categoría {profile['age']} años, "
             f"llevando con orgullo los colores de {club}.")

    return Template(_TEMPLATE).substitute(
        name_first=first,
        name_rest=rest,
        category=f"{profile['age']} AÑOS",
        club=club,
        league=league,
        gender=gender,
        birth=escape(str(profile["birth_date"] or "—")),
        ref_year=profile["reference_year"],
        photo=photo,
        logo=logo,
        champ=champ_html,
        highlights=_highlights_html(profile, h),
        rows=_rows_html(list(profile["top_events"])),
        quote=quote,
    )


_TEMPLATE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root{
    --navy:#0b2447; --navy2:#0f3160; --gold:#f6b500; --gold2:#ffd45e;
    --ink:#10243f; --paper:#f4f6fb;
  }
  *{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;}
  .card{width:100%;max-width:760px;margin:0 auto;
        container-type:inline-size;container-name:ficha;
        background:linear-gradient(160deg,#0b2447,#123a6b);
        color:#fff;overflow:hidden;border-radius:14px;}
  .hero{position:relative;display:flex;flex-wrap:wrap;gap:18px;padding:22px 26px 16px;}
  .hero .photo{width:210px;height:230px;object-fit:cover;border-radius:10px;
        border:3px solid rgba(255,255,255,.15);}
  .hero-main{flex:1;display:flex;flex-direction:column;}
  .toprow{display:flex;align-items:center;gap:12px;}
  .logo{width:88px;height:88px;object-fit:contain;}
  .name{margin-top:6px;line-height:.95;overflow-wrap:anywhere;word-break:break-word;}
  .name .first{font-size:clamp(26px,8cqw,54px);font-weight:800;letter-spacing:1px;}
  .name .last{font-size:clamp(26px,8cqw,54px);font-weight:800;color:var(--gold);letter-spacing:1px;}
  .badge{display:inline-block;margin-top:12px;background:var(--gold);color:var(--ink);
        font-weight:800;font-size:18px;padding:7px 16px;border-radius:20px;align-self:flex-start;}
  .club{margin-top:8px;color:var(--gold2);font-weight:700;letter-spacing:2px;font-size:14px;}
  .champ{margin-top:auto;text-align:right;}
  .champ-name{font-weight:800;font-size:16px;color:#cfe0ff;}
  .champ-venue{font-size:13px;color:var(--gold2);letter-spacing:3px;}
  .hls{display:flex;flex-direction:column;gap:10px;padding:4px 26px 6px;}
  .hl{border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:16px;}
  .hl-gold{background:linear-gradient(90deg,#14315e,#1c4a8a);border:1px solid var(--gold);}
  .hl-silver{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.18);
        flex-direction:column;align-items:stretch;}
  .hl-medal{font-size:40px;}
  .hl-title{font-weight:800;font-size:22px;color:var(--gold);letter-spacing:1px;}
  .hl-detail{margin-left:auto;text-align:right;display:flex;flex-direction:column;}
  .hl-detail b{font-size:16px;}
  .hl-detail span{font-size:15px;color:#dbe6ff;}
  .hl-pos{color:var(--gold2)!important;font-weight:700;}
  .chips{display:flex;gap:10px;margin-top:8px;}
  .chip{flex:1;background:rgba(0,0,0,.25);border-radius:8px;padding:8px 10px;
        display:flex;flex-direction:column;text-align:center;}
  .chip b{font-size:14px;}
  .chip span{font-size:13px;color:#dbe6ff;}
  .tablewrap{margin:12px 26px 6px;overflow-x:auto;-webkit-overflow-scrolling:touch;
        border-radius:10px;}
  table{width:100%;min-width:0;border-collapse:collapse;
        background:var(--paper);color:var(--ink);border-radius:10px;overflow:hidden;}
  thead th{background:var(--navy);color:#fff;font-size:13px;letter-spacing:.5px;
        padding:11px 12px;text-align:left;}
  tbody td{padding:11px 12px;border-top:1px solid #e3e8f2;font-size:15px;}
  tbody tr:nth-child(even){background:#eef2fa;}
  td.ev{font-weight:700;}
  td.ev .pool{margin-left:8px;font-size:11px;color:#fff;background:var(--navy2);
        padding:2px 7px;border-radius:10px;vertical-align:middle;}
  td.time{font-weight:800;color:var(--navy2);}
  .of{color:#6b7a92;font-weight:500;font-size:13px;}
  .foot{padding:14px 26px 22px;text-align:center;font-style:italic;color:#cfe0ff;
        font-size:14px;line-height:1.5;}
  .foot b{color:var(--gold);font-style:normal;}
  .ref{padding:0 26px 18px;text-align:center;color:#8aa3c9;font-size:11px;}
  @container ficha (max-width:560px){
    .hero{flex-direction:column;align-items:center;text-align:center;padding:18px 14px 12px;}
    .hero .photo{width:100%;max-width:280px;height:auto;}
    .name{margin-top:10px;}
    .badge,.club,.champ{align-self:center;text-align:center;}
    .badge{font-size:15px;}
    .club{font-size:12px;}
    .champ{margin-top:12px;}
    .champ-name{font-size:14px;}
    .hl{flex-direction:column;align-items:flex-start;gap:8px;}
    .hl-title{font-size:18px;}
    .hl-medal{font-size:30px;}
    .hl-detail{margin-left:0;text-align:left;}
    .chips{flex-direction:column;}
    .tablewrap{margin:10px 10px 6px;}
    thead th,tbody td{padding:7px 6px;font-size:12px;}
    td.time{font-size:12px;}
    .of{font-size:11px;}
    td.ev .pool{font-size:10px;padding:1px 5px;}
    .foot,.ref{padding-left:14px;padding-right:14px;}
  }
</style></head>
<body>
  <div class="card">
    <div class="hero">
      $photo
      <div class="hero-main">
        <div class="toprow">$logo</div>
        <div class="name"><div class="first">$name_first</div>
          <div class="last">$name_rest</div></div>
        <div class="badge">$category &nbsp;·&nbsp; $gender</div>
        <div class="club">$club &nbsp;·&nbsp; LIGA $league</div>
        $champ
      </div>
    </div>
    <div class="hls">
      $highlights
    </div>
    <div class="tablewrap"><table>
      <thead><tr><th>Prueba</th><th>Mejor marca</th>
        <th>🏆 Ranking liga</th><th>🇨🇴 Ranking Colombia</th></tr></thead>
      <tbody>
        $rows
      </tbody>
    </table></div>
    <div class="foot">“$quote”</div>
    <div class="ref">Categoría calculada al año $ref_year · Nacimiento: $birth ·
      Puesto por género y categoría · Fuente: ranking FECNA</div>
  </div>
</body></html>"""
