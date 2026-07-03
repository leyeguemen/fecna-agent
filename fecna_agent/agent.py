"""Agente de consulta: pregunta en lenguaje natural → respuesta con datos exactos.

Flujo (sección 8 del spec):
  1. resolver.parse_question  → intención, ids, piscina, género
  2. semantic.resolve_event   → "50 libre" → event_id
  3. db.*                     → marcas exactas desde SQLite
  4. Formato de respuesta con los datos usados (sin inventar nada)
"""

import re

from . import db as database
from . import semantic
from .resolver import normalize, parse_question
from .times import ms_to_time

# Pronombres/referencias que indican una pregunta de seguimiento sobre el mismo
# nadador del turno anterior ("¿y su evolución?", "compáralo con ...").
_PRONOUN_RE = re.compile(r"\b(su|sus|ese|esa|este|esta|mismo|misma|suyo|suya|lo)\b")


_HELP = (
    "No entendí la pregunta. Puedo responder, por ejemplo:\n"
    "  - mejor marca de <nombre o identificación> en 50 libre\n"
    "  - compara <id1> con <id2> en 100 espalda piscina larga\n"
    "  - ranking femenino de 12 años en 200 combinado\n"
    "  - evolución de <nombre> en 100 pecho"
)


def _dispatch(conn, parsed, event, client, embedding) -> str:
    # Nada reconocible (ni intención, ni nadador, ni prueba): guía en vez de
    # adivinar y responder cualquier cosa con seguridad.
    if (not parsed.explicit_intent and not parsed.swimmer_ids
            and not parsed.name_query and not event):
        return _HELP
    if parsed.intent == "compare":
        return _compare(conn, parsed, event)
    if parsed.intent == "ranking":
        return _ranking(conn, parsed, event)
    if parsed.intent == "history":
        return _history(conn, parsed, event, client, embedding)
    return _best(conn, parsed, event, client, embedding)


def answer(
    conn,
    question: str,
    persist_dir=semantic.DEFAULT_PERSIST_DIR,
    use_llm: bool = False,
    llm_model: str | None = None,
) -> str:
    parsed = parse_question(question)
    embedding = semantic.load_embedding_name(persist_dir)
    client = semantic.get_client(persist_dir)
    event = semantic.resolve_event(client, parsed.event_query or question, embedding)
    facts = _dispatch(conn, parsed, event, client, embedding)
    if use_llm:
        return redact_with_llm(question, facts, llm_model)
    return facts


def _merge_context(parsed, context: dict):
    """Completa la pregunta actual con el contexto del turno anterior cuando
    faltan datos: prueba, piscina y género se heredan si no se mencionan; el
    nadador se hereda solo si hay un pronombre de seguimiento (o para completar
    el par en una comparación). Así 'y su evolución' o 'compáralo con X' usan el
    nadador previo, pero una pregunta nueva con nombre/identificación no."""
    if not parsed.event_query and context.get("event_query"):
        parsed.event_query = context["event_query"]
    if not parsed.pool_type and context.get("pool_type"):
        parsed.pool_type = context["pool_type"]
    if not parsed.gender and context.get("gender"):
        parsed.gender = context["gender"]

    prev_ids = context.get("swimmer_ids") or []
    if parsed.intent == "compare":
        for sid in prev_ids:
            if len(parsed.swimmer_ids) >= 2:
                break
            if sid not in parsed.swimmer_ids:
                parsed.swimmer_ids.append(sid)
    elif not parsed.swimmer_ids and prev_ids and _PRONOUN_RE.search(normalize(parsed.raw)):
        parsed.swimmer_ids = [prev_ids[0]]
    return parsed


def chat_answer(
    conn,
    question: str,
    context: dict | None = None,
    persist_dir=semantic.DEFAULT_PERSIST_DIR,
    use_llm: bool = False,
    llm_model: str | None = None,
) -> tuple[str, dict]:
    """Como answer(), pero conversacional: recuerda el contexto del turno previo.
    Devuelve (respuesta, nuevo_contexto) para encadenar la conversación."""
    parsed = _merge_context(parse_question(question), context or {})
    embedding = semantic.load_embedding_name(persist_dir)
    client = semantic.get_client(persist_dir)
    event = semantic.resolve_event(client, parsed.event_query or question, embedding)
    facts = _dispatch(conn, parsed, event, client, embedding)

    new_context = {
        "swimmer_ids": parsed.swimmer_ids,
        "event_query": parsed.event_query or (event["event_name"] if event else None),
        "pool_type": parsed.pool_type,
        "gender": parsed.gender,
    }
    reply = redact_with_llm(question, facts, llm_model) if use_llm else facts
    return reply, new_context


def redact_with_llm(question: str, facts: str, model: str | None = None) -> str:
    """Redacción natural con Ollama; si falla, devuelve los datos calculados.
    Los datos siempre se anexan: el LLM explica, no es la fuente de verdad."""
    from . import llm

    try:
        if not llm.is_available():
            return f"{facts}\n\n(Ollama no disponible; respuesta determinística.)"
        natural = llm.rephrase(question, facts, model=model)
    except Exception as exc:
        return f"{facts}\n\n(LLM local falló: {exc}; respuesta determinística.)"
    return f"{natural}\n\n— Datos calculados (SQL/Python) —\n{facts}"


def _swimmer_id(parsed, client, embedding) -> tuple[str | None, str | None, str | None]:
    """Identificación del nadador → (id, nombre_interpretado, error).

    Por id explícito, o por nombre validado contra la base. Si el nombre no
    está o es ambiguo (homónimos), devuelve el mensaje en `error` en vez de
    adivinar."""
    if parsed.swimmer_ids:
        return parsed.swimmer_ids[0], None, None
    query = parsed.name_query or parsed.raw
    candidates = semantic.resolve_swimmer_candidates(client, query, embedding)
    if not candidates:
        who = f" «{parsed.name_query}»" if parsed.name_query else ""
        return None, None, (
            f"No encontré al nadador{who} en la base. "
            "Prueba con el nombre completo o su identificación."
        )
    top = [c for c in candidates if c["score"] == candidates[0]["score"]]
    if len(top) > 1:
        options = "\n".join(f"  - {c['swimmer_name']} ({c['swimmer_id']})" for c in top)
        return None, None, (
            "Hay varios nadadores que coinciden:\n" + options +
            "\nRepite la pregunta con la identificación del que te interesa."
        )
    return top[0]["swimmer_id"], top[0]["swimmer_name"], None


def _compare(conn, parsed, event) -> str:
    if len(parsed.swimmer_ids) < 2:
        return "Para comparar necesito dos identificaciones de nadadores."
    if not event:
        return "No pude identificar la prueba. Ejecuta primero: python -m fecna_agent index"

    result = database.compare_swimmers(
        conn, parsed.swimmer_ids[0], parsed.swimmer_ids[1],
        event["event_id"], parsed.pool_type,
    )
    a, b = result["a"], result["b"]
    missing = [sid for sid, row in zip(parsed.swimmer_ids[:2], (a, b)) if not row]
    if missing:
        return (f"Sin resultados en {event['event_name']} para: {', '.join(missing)}. "
                f"¿Ya extrajiste esa prueba con 'fetch --prueba {event['event_id']}'?")

    faster, slower = (a, b) if a["time_ms"] <= b["time_ms"] else (b, a)
    pool = f" piscina {'larga' if parsed.pool_type == 'LC' else 'corta'}" if parsed.pool_type else ""
    return (
        f"En {event['event_name']}{pool}, {faster['swimmer_name']} tiene mejor marca "
        f"que {slower['swimmer_name']}.\n\n"
        f"  {a['swimmer_name']}: {a['time_raw']} ({a['result_date']})\n"
        f"  {b['swimmer_name']}: {b['time_raw']} ({b['result_date']})\n"
        f"  Diferencia: {result['diff_ms'] / 1000:.2f} segundos "
        f"({result['diff_ms'] / slower['time_ms'] * 100:.2f}%)."
    )


def _best(conn, parsed, event, client, embedding) -> str:
    swimmer_id, matched_name, error = _swimmer_id(parsed, client, embedding)
    if not swimmer_id:
        return error or "No pude identificar al nadador."

    row = database.best_time(
        conn, swimmer_id,
        event["event_id"] if event else None,
        parsed.pool_type,
    )
    if not row:
        return f"Sin resultados locales para el nadador {swimmer_id} con esos filtros."

    note = f" (interpreté el nombre como {matched_name})" if matched_name else ""
    return (
        f"Mejor marca de {row['swimmer_name']} ({swimmer_id}){note}:\n"
        f"  {row['event_name']} [{row['pool_type']}]: {row['time_raw']} ({row['result_date']})"
    )


def _ranking(conn, parsed, event) -> str:
    from .categories import age_range

    if not event:
        return "No pude identificar la prueba del ranking."
    rows = database.ranking(
        conn, event["event_id"], parsed.pool_type, parsed.gender, limit=10,
        age_range=age_range(parsed.category) if parsed.category else None,
    )
    if not rows:
        return (f"Sin resultados locales para {event['event_name']}. "
                f"Extrae primero con 'fetch --prueba {event['event_id']}'.")
    header = f"Ranking {event['event_name']}"
    if parsed.pool_type:
        header += f" [{parsed.pool_type}]"
    if parsed.category:
        header += f" — {parsed.category}"
    lines = [header + ":"]
    for pos, row in enumerate(rows, 1):
        lines.append(f"  {pos:>2}. {ms_to_time(row['time_ms'])}  {row['swimmer_name']}"
                     f"  ({row['club']} / {row['league']})")
    return "\n".join(lines)


def _history(conn, parsed, event, client, embedding) -> str:
    swimmer_id, matched_name, error = _swimmer_id(parsed, client, embedding)
    if not swimmer_id:
        return error or "No pude identificar al nadador para ver su evolución."
    rows = database.history(
        conn, swimmer_id,
        event["event_id"] if event else None,
        parsed.pool_type,
    )
    if not rows:
        return f"Sin resultados locales para el nadador {swimmer_id}."
    note = f" (interpreté el nombre como {matched_name})" if matched_name else ""
    lines = [f"Evolución de {rows[0]['swimmer_name']} ({swimmer_id}){note}:"]
    for row in rows:
        lines.append(f"  {row['result_date']}  {row['time_raw']}  "
                     f"{row['event_name']} [{row['pool_type']}]")
    return "\n".join(lines)
