"""Redacción de respuestas naturales con un LLM local (Ollama).

Regla del proyecto: el LLM solo explica. Recibe los datos ya calculados por
SQL/Python y los redacta; nunca calcula ni inventa cifras. Si Ollama no está
disponible, el agente responde con el texto determinístico de siempre.
"""

import os

import requests

BASE_URL = os.environ.get("FECNA_OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("FECNA_OLLAMA_MODEL", "")  # vacío = primer modelo local

PROMPT = """Eres el redactor de un agente de consulta de resultados de natación.

Pregunta del usuario:
{question}

Datos calculados por el sistema (única fuente de verdad):
{facts}

Redacta en español una respuesta breve y natural a la pregunta usando
EXCLUSIVAMENTE los datos de arriba.
Reglas estrictas:
- No inventes, no estimes y no recalcules ninguna cifra.
- Copia los tiempos, fechas, diferencias y porcentajes tal cual aparecen.
- Si los datos indican que falta información, dilo sin adornar.
- Máximo un párrafo corto, sin encabezados.

Respuesta:"""


def is_available(base_url: str | None = None) -> bool:
    try:
        requests.get(f"{base_url or BASE_URL}/api/tags", timeout=2).raise_for_status()
        return True
    except requests.RequestException:
        return False


def list_models(base_url: str | None = None) -> list[str]:
    response = requests.get(f"{base_url or BASE_URL}/api/tags", timeout=5)
    response.raise_for_status()
    return [m["name"] for m in response.json().get("models", [])]


def resolve_model(model: str | None = None, base_url: str | None = None) -> str:
    model = model or DEFAULT_MODEL
    if model:
        return model
    models = list_models(base_url)
    if not models:
        raise RuntimeError("Ollama no tiene modelos instalados (ollama pull llama3)")
    return models[0]


def build_prompt(question: str, facts: str) -> str:
    return PROMPT.format(question=question, facts=facts)


def rephrase(
    question: str,
    facts: str,
    model: str | None = None,
    base_url: str | None = None,
    timeout: int = 120,
) -> str:
    """Pide al modelo local redactar la respuesta a partir de los datos calculados."""
    payload = {
        "model": resolve_model(model, base_url),
        "prompt": build_prompt(question, facts),
        "stream": False,
        "options": {"temperature": 0.2},
    }
    response = requests.post(f"{base_url or BASE_URL}/api/generate", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()["response"].strip()
