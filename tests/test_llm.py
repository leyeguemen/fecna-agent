from fecna_agent import llm
from fecna_agent.agent import redact_with_llm

FACTS = "Nadador A: 00:00:28.31\nNadador B: 00:00:29.54\nDiferencia: 1.23 segundos."
QUESTION = "¿Quién es más rápido en 50 libre?"


def test_prompt_incluye_pregunta_datos_y_reglas():
    prompt = llm.build_prompt(QUESTION, FACTS)
    assert QUESTION in prompt
    assert FACTS in prompt
    assert "No inventes" in prompt


def test_fallback_si_ollama_no_disponible(monkeypatch):
    monkeypatch.setattr(llm, "is_available", lambda: False)
    result = redact_with_llm(QUESTION, FACTS)
    assert FACTS in result
    assert "Ollama no disponible" in result


def test_fallback_si_el_llm_falla(monkeypatch):
    monkeypatch.setattr(llm, "is_available", lambda: True)

    def boom(*args, **kwargs):
        raise RuntimeError("conexión rechazada")

    monkeypatch.setattr(llm, "rephrase", boom)
    result = redact_with_llm(QUESTION, FACTS)
    assert FACTS in result
    assert "respuesta determinística" in result


def test_respuesta_natural_siempre_anexa_los_datos(monkeypatch):
    monkeypatch.setattr(llm, "is_available", lambda: True)
    monkeypatch.setattr(llm, "rephrase", lambda *a, **k: "El nadador A es más rápido.")
    result = redact_with_llm(QUESTION, FACTS)
    assert result.startswith("El nadador A es más rápido.")
    assert FACTS in result  # los datos calculados nunca se ocultan
