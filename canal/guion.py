"""Investigación y guion con Claude (API de Anthropic).

Paso 1: investiga el tema en la web (búsqueda de Claude) y reúne hechos con fuentes.
Paso 2: escribe el guion de documental en JSON usando solo esos hechos.
Sin ANTHROPIC_API_KEY se usan los guiones ya escritos en /guiones.
"""
import json
from pathlib import Path

import anthropic

from .util import GUIONES, slug

ESCENA = {
    "type": "object",
    "properties": {
        "narracion": {"type": "string"},
        "tipo": {"type": "string", "enum": ["broll", "foto", "titulo", "dato", "cita"]},
        "fuente": {"type": "string", "enum": ["stock", "archivo"]},
        "busqueda": {"type": "string"},
        "texto": {"type": "string"},
        "subtexto": {"type": "string"},
        "etiqueta": {"type": "string"},
    },
    "required": ["narracion", "tipo", "fuente", "busqueda", "texto", "subtexto", "etiqueta"],
    "additionalProperties": False,
}

ESQUEMA = {
    "type": "object",
    "properties": {
        "tema": {"type": "string"},
        "titulo": {"type": "string"},
        "descripcion": {"type": "string"},
        "etiquetas": {"type": "array", "items": {"type": "string"}},
        "miniatura": {
            "type": "object",
            "properties": {
                "texto": {"type": "string"},
                "etiqueta": {"type": "string"},
                "fuente": {"type": "string", "enum": ["stock", "archivo"]},
                "busqueda": {"type": "string"},
            },
            "required": ["texto", "etiqueta", "fuente", "busqueda"],
            "additionalProperties": False,
        },
        "fuentes": {"type": "array", "items": {"type": "string"}},
        "resumen_es": {"type": "string"},
        "escenas": {"type": "array", "items": ESCENA},
        "short": {
            "type": "object",
            "properties": {
                "titulo": {"type": "string"},
                "descripcion": {"type": "string"},
                "escenas": {"type": "array", "items": ESCENA},
            },
            "required": ["titulo", "descripcion", "escenas"],
            "additionalProperties": False,
        },
    },
    "required": ["tema", "titulo", "descripcion", "etiquetas", "miniatura", "fuentes", "resumen_es", "escenas", "short"],
    "additionalProperties": False,
}

IDIOMAS = {"en": "inglés (Estados Unidos)", "es": "español latinoamericano neutro"}


def _cliente() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def investigar(tema: str, cfg: dict) -> str:
    """Busca en la web y devuelve notas con hechos verificados y sus URLs."""
    client = _cliente()
    pedido = f"""Investiga a fondo esta historia para un documental de YouTube: {tema}

Busca en fuentes confiables (medios reconocidos, documentos judiciales, comunicados oficiales, libros, entrevistas). Devuelve notas en español con:
- Cronología con fechas exactas.
- Personas clave y su papel (solo datos públicos y verificables).
- Cifras concretas, cada una con la fuente que la respalda.
- Citas textuales reales (con quién las dijo y dónde).
- Detalles poco conocidos o giros que hagan la historia interesante.
- Qué datos son dudosos o contradictorios entre fuentes.
- Lista final de URLs usadas.
No inventes nada: si un dato no aparece en las fuentes, no lo incluyas."""
    mensajes = [{"role": "user", "content": pedido}]
    for _ in range(6):  # continúa si la búsqueda se pausa (pause_turn)
        r = client.beta.messages.create(
            model=cfg["guion"]["modelo"],
            max_tokens=32000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "high"},
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 15}],
            messages=mensajes,
        )
        if r.stop_reason != "pause_turn":
            break
        mensajes = [mensajes[0], {"role": "assistant", "content": r.content}]
    if r.stop_reason == "refusal":
        raise RuntimeError(f"Claude no investigó el tema '{tema}'. Elige otro.")
    return "\n".join(b.text for b in r.content if b.type == "text")


def _sistema(cfg: dict) -> str:
    c = cfg["canal"]
    idioma = IDIOMAS[c["idioma"]]
    palabras = cfg["guion"]["palabras_video_largo"]
    return f"""Eres el guionista principal de "{c['nombre']}", un canal de YouTube de documentales.
Nicho: {c['nicho']}.
Público: {c['publico']}.
Idioma de la narración, títulos y textos en pantalla: {idioma}.

Identidad del canal: cada video es un "expediente" (case file) de un crimen o desastre financiero real, narrado con tono de cine negro: sobrio, intrigante, preciso, con una voz que investiga. El espectador debe sentir que revisa las pruebas junto al narrador: fechas, documentos, cifras, decisiones y consecuencias. Nunca hagas videos de predicciones, miedo económico ("el próximo crash", "tus ahorros desaparecerán") ni consejos de inversión: eso es lo que hacen los canales genéricos y no es nuestro estilo.

Estructura del video largo (unas {palabras} palabras de narración, 35 a 60 escenas):
1. Gancho (primeros 20-30 segundos): empieza en el momento más dramático o con la pregunta más intrigante. Nada de saludos ni "en este video".
2. Promesa: qué va a descubrir el espectador y por qué le importa.
3. Desarrollo en 3 a 5 capítulos (cada uno abre con una escena tipo "titulo"), con causa y efecto claros, giros y pequeños cliffhangers al final de cada capítulo.
4. Desenlace y lección: qué pasó al final y qué podemos aprender.
5. Cierre: pregunta para comentarios y una invitación breve a suscribirse (no antes del minuto 2).

Reglas de precisión: usa SOLO los hechos de las notas de investigación. No inventes cifras, fechas, citas ni diálogos. Si algo es una suposición, dilo como tal ("según los fiscales", "se cree que").

Escenas (cada una dura 4-10 segundos de narración, 1-2 frases):
- "broll": video de stock que ilustra la narración. fuente "stock"; "busqueda" = 2-4 palabras EN INGLÉS de algo filmable (ej. "hacker typing dark room", "bitcoin price chart", "courtroom gavel"). Sin marcas ni famosos.
- "foto": foto real de una persona, lugar, empresa o documento. fuente "archivo"; "busqueda" = nombre exacto en inglés para Wikimedia Commons (ej. "Twitter headquarters San Francisco", "Barack Obama 2020"). Úsala solo para cosas que probablemente tengan foto libre.
- "titulo": inicio de capítulo. "texto" = título corto (2-5 palabras); "subtexto" = "CHAPTER 1" (en el idioma del canal). La PRIMERA escena tipo "titulo", justo después del gancho, es la portada del expediente: "texto" = nombre corto del caso (ej. "The Twitter Heist"), "subtexto" = "CASE FILE". Busca un fondo de stock que encaje.
- "dato": una cifra impactante. "texto" = la cifra tal cual se mostrará (ej. "$118,000", "130", "17"); "subtexto" = qué significa (máx. 8 palabras).
- "cita": cita textual real de las notas. "texto" = la cita; "subtexto" = quién la dijo.
- "etiqueta": rótulo opcional de lugar/fecha para broll y foto (ej. "JULY 15, 2020 · SAN FRANCISCO"), o cadena vacía.
- Campos que no apliquen: cadena vacía.
- Ritmo: alterna tipos; nunca más de 3 broll seguidos; usa titulo/dato/cita con moderación (en total 15-25% de las escenas).
- La narración debe sonar natural leída por una voz sintética: frases de largo variado, sin paréntesis, sin abreviaturas raras; escribe los años y cifras como se leen si hay ambigüedad.

Metadatos:
- "titulo": máximo 65 caracteres, curiosidad + honestidad, en el idioma del canal.
- "miniatura.texto": 2-4 palabras en mayúsculas en el idioma del canal, con UNA palabra clave entre asteriscos (ej. "HE HACKED *TWITTER*"); distinto del título. "miniatura.etiqueta": 1-3 palabras de impacto (ej. "AGE 17") o vacío. "miniatura.busqueda": la imagen más llamativa (persona o lugar clave).
- "descripcion": 2 párrafos atractivos con palabras clave naturales + 3 hashtags (las fuentes y créditos se añaden solos).
- "fuentes": las URLs de las notas.
- "resumen_es": resumen en ESPAÑOL de 4-6 frases para que el dueño del canal revise el contenido.
- "short": video vertical independiente de 110-150 palabras (45-60 s), 6-10 escenas, con el momento más impactante de la historia y un final que invite a ver el video completo. Título con #shorts."""


def escribir(tema: str, notas: str, cfg: dict) -> dict:
    client = _cliente()
    with client.beta.messages.stream(
        model=cfg["guion"]["modelo"],
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": cfg["guion"]["esfuerzo"], "format": {"type": "json_schema", "schema": ESQUEMA}},
        system=_sistema(cfg),
        messages=[{"role": "user", "content": f"Tema: {tema}\n\nNotas de investigación:\n{notas}\n\nEscribe el guion completo."}],
    ) as stream:
        r = stream.get_final_message()
    if r.stop_reason == "refusal":
        raise RuntimeError(f"Claude rechazó el tema '{tema}'.")
    if r.stop_reason == "max_tokens":
        raise RuntimeError("El guion se cortó por longitud; vuelve a intentarlo.")
    guion = json.loads(next(b.text for b in r.content if b.type == "text"))
    guion["tema"] = tema
    return guion


def generar_guion(tema: str, cfg: dict) -> dict:
    print("  Investigando en la web...")
    notas = investigar(tema, cfg)
    GUIONES.mkdir(exist_ok=True)
    (GUIONES / f"{slug(tema)}.notas.md").write_text(notas, encoding="utf-8")
    print("  Escribiendo guion...")
    return escribir(tema, notas, cfg)


def guardar_guion(guion: dict) -> Path:
    GUIONES.mkdir(exist_ok=True)
    ruta = GUIONES / f"{slug(guion['tema'])}.json"
    ruta.write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def cargar_guion(ruta: Path) -> dict:
    guion = json.loads(Path(ruta).read_text(encoding="utf-8"))
    faltan = [k for k in ESQUEMA["required"] if k not in guion]
    if faltan:
        raise ValueError(f"Al guion {ruta} le faltan campos: {faltan}")
    return guion
