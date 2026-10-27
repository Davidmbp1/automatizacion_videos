"""Narración con voces gratuitas y de uso comercial permitido.

- kokoro (Apache 2.0): muy natural en inglés, rápido en CPU. Motor por defecto.
- chatterbox (MIT): clona una voz de referencia; el más humano en español. Lento en CPU.
- edge (Microsoft Edge TTS): respaldo en línea.
"""
import asyncio
import hashlib
from pathlib import Path

import requests

from .util import CACHE, ejecutar

KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
_kokoro = None
_chatterbox = None


def _descargar(url: str, destino: Path) -> Path:
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        print(f"  Descargando {destino.name}...")
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            tmp = destino.with_suffix(".part")
            with open(tmp, "wb") as f:
                for trozo in r.iter_content(1 << 20):
                    f.write(trozo)
            tmp.rename(destino)
    return destino


def _con_kokoro(texto: str, salida: Path, v: dict) -> None:
    global _kokoro
    import soundfile as sf
    from kokoro_onnx import Kokoro

    if _kokoro is None:
        modelos = CACHE / "modelos"
        _kokoro = Kokoro(str(_descargar(KOKORO_URL + "kokoro-v1.0.onnx", modelos / "kokoro-v1.0.onnx")),
                         str(_descargar(KOKORO_URL + "voices-v1.0.bin", modelos / "voices-v1.0.bin")))
    audio, sr = _kokoro.create(texto, voice=v["kokoro_voz"], speed=v["velocidad"], lang=v["kokoro_idioma"])
    sf.write(str(salida), audio, sr)


def _con_chatterbox(texto: str, salida: Path, v: dict) -> None:
    global _chatterbox
    import torch
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    if _chatterbox is None:
        _chatterbox = ChatterboxMultilingualTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
        if v["idioma"] == "es":
            # pesos oficiales ajustados para español latinoamericano (MIT)
            from huggingface_hub import hf_hub_download
            from safetensors.torch import load_file

            pesos = hf_hub_download("ResembleAI/Chatterbox-Multilingual-es-mx-latam", "t3_es_mx_latam.safetensors")
            _chatterbox.t3.load_state_dict(load_file(pesos))
    ref = v.get("chatterbox_referencia") or None
    # Chatterbox rinde mejor frase por frase
    frases = [f.strip() for f in texto.replace("?", "?|").replace("!", "!|").replace(". ", ".|").split("|") if f.strip()]
    partes = []
    for f in frases:
        partes += [_chatterbox.generate(f, language_id=v["idioma"], audio_prompt_path=ref,
                                        exaggeration=v.get("chatterbox_expresividad", 0.5)),
                   torch.zeros(1, int(_chatterbox.sr * 0.18))]
    ta.save(str(salida), torch.cat(partes, dim=1), _chatterbox.sr)


def _con_edge(texto: str, salida: Path, v: dict) -> None:
    import edge_tts

    mp3 = salida.with_suffix(".mp3")

    async def _run():
        await edge_tts.Communicate(texto, v["edge_voz"]).save(str(mp3))

    asyncio.run(_run())
    ejecutar(["ffmpeg", "-y", "-i", str(mp3), str(salida)])
    mp3.unlink(missing_ok=True)


MOTORES = {"kokoro": _con_kokoro, "chatterbox": _con_chatterbox, "edge": _con_edge}


def narrar(texto: str, cfg: dict) -> Path:
    """Genera la narración de un texto en WAV (con caché) y devuelve la ruta."""
    v = cfg["voz"]
    clave = hashlib.sha1(f"{sorted(v.items())}|{texto}".encode()).hexdigest()[:16]
    salida = CACHE / "voz" / f"{v['motor']}-{clave}.wav"
    if salida.exists():
        return salida
    salida.parent.mkdir(parents=True, exist_ok=True)
    orden = [v["motor"]] + [m for m in ("kokoro", "edge") if m != v["motor"]]
    for motor in orden:
        try:
            MOTORES[motor](texto, salida, v)
            return salida
        except Exception as e:
            print(f"  Voz '{motor}' falló ({type(e).__name__}: {e}); probando la siguiente.")
            salida.unlink(missing_ok=True)
    raise RuntimeError("Ningún motor de voz funcionó.")
