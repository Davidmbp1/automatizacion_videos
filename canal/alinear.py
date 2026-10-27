"""Tiempos palabra por palabra de la narración con Whisper (faster-whisper, MIT).

Whisper solo aporta los tiempos: el texto mostrado es siempre el del guion, para que nombres
propios y cifras salgan bien escritos aunque Whisper los entienda mal.
"""
import re
import subprocess
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

_modelos: dict = {}


def _leer_audio(audio: Path) -> np.ndarray:
    """Decodifica a 16 kHz mono con FFmpeg (evita depender de la versión de PyAV)."""
    crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                           capture_output=True, check=True).stdout
    return np.frombuffer(crudo, np.int16).astype(np.float32) / 32768.0


def _normal(palabra: str) -> str:
    return re.sub(r"[^\w]", "", palabra.lower())


def _whisper(audio: np.ndarray, idioma: str) -> list[tuple[str, float, float]]:
    from faster_whisper import WhisperModel

    nombre = "base.en" if idioma == "en" else "small"
    if nombre not in _modelos:
        _modelos[nombre] = WhisperModel(nombre, device="cpu", compute_type="int8")
    segmentos, _ = _modelos[nombre].transcribe(audio, language=idioma, word_timestamps=True,
                                               vad_filter=False, condition_on_previous_text=False)
    return [(w.word.strip(), w.start, w.end) for s in segmentos for w in (s.words or []) if w.word.strip()]


def palabras_con_tiempos(audio: Path, idioma: str, texto: str, desfase: float = 0.0) -> list[dict]:
    """Palabras del guion (`texto`) con su inicio y fin en segundos, desplazados `desfase`."""
    señal = _leer_audio(audio)
    total = len(señal) / 16000
    guion = texto.split()
    oidas = _whisper(señal, idioma)

    # anclas: palabras del guion que Whisper reconoció igual
    tiempos: list[tuple[float, float] | None] = [None] * len(guion)
    sm = SequenceMatcher(a=[_normal(p) for p in guion], b=[_normal(w[0]) for w in oidas], autojunk=False)
    for bloque in sm.get_matching_blocks():
        for k in range(bloque.size):
            _, ini, fin = oidas[bloque.b + k]
            tiempos[bloque.a + k] = (ini, fin)

    # el resto se reparte entre las anclas vecinas según el largo de cada palabra
    i = 0
    while i < len(guion):
        if tiempos[i] is not None:
            i += 1
            continue
        j = i
        while j < len(guion) and tiempos[j] is None:
            j += 1
        desde = tiempos[i - 1][1] if i > 0 else 0.0
        hasta = tiempos[j][0] if j < len(guion) else min(total, (oidas[-1][2] if oidas else total))
        hasta = max(hasta, desde + 0.05 * (j - i))
        pesos = [len(p) + 1 for p in guion[i:j]]
        t = desde
        for k, peso in zip(range(i, j), pesos):
            dur = (hasta - desde) * peso / sum(pesos)
            tiempos[k] = (t, t + dur)
            t += dur
        i = j

    return [{"texto": p, "inicio": round(a + desfase, 3), "fin": round(b + desfase, 3)} for p, (a, b) in zip(guion, tiempos)]
