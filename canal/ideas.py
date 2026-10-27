"""Ideas de temas nuevos con Claude, evitando repetir los existentes."""
import json

import anthropic


def generar_ideas(n: int, existentes: list[str], cfg: dict) -> list[str]:
    c = cfg["canal"]
    lista = "\n".join(f"- {t}" for t in existentes) or "(ninguno)"
    r = anthropic.Anthropic().beta.messages.create(
        model=cfg["guion"]["modelo"],
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": {
                "type": "object",
                "properties": {"temas": {"type": "array", "items": {"type": "string"}}},
                "required": ["temas"], "additionalProperties": False,
            }},
        },
        messages=[{"role": "user", "content": f"""Propón {n} historias reales para documentales del canal de YouTube "{c['nombre']}".
Nicho: {c['nicho']}. Público: {c['publico']}.

Criterios:
- Historias verdaderas y bien documentadas (con fuentes públicas: prensa, juicios, informes oficiales).
- Con personajes, tensión y un giro: ascenso y caída, fraude descubierto, golpe que casi sale bien, decisión que costó miles de millones.
- Mezcla historias muy conocidas (que la gente busca) con otras poco contadas (menos competencia).
- Evita temas que se puedan quedar viejos en semanas y evita a personas privadas que no sean figuras públicas.
Escribe cada tema como una frase descriptiva concreta en español (personaje + qué pasó + año aproximado).

No repitas ni parafrasees estos temas:
{lista}"""}],
    )
    if r.stop_reason == "refusal":
        raise RuntimeError("Claude no generó ideas; inténtalo de nuevo.")
    texto = next(b.text for b in r.content if b.type == "text")
    return [t.strip() for t in json.loads(texto)["temas"] if t.strip()][:n]
