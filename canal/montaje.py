"""Prepara narración, visuales y subtítulos, y renderiza con el editor Remotion (carpeta editor/)."""
import json
import random
import shutil
import subprocess
from pathlib import Path

from .alinear import palabras_con_tiempos
from .medios import obtener_visual
from .util import EDITOR, MUSICA, PUBLIC, duracion, ejecutar
from .voz import narrar

PAUSA = 0.35  # silencio tras cada escena
PAUSA_TARJETA = 0.6  # un poco más tras títulos, datos y citas
TARJETAS = ("titulo", "dato", "cita")


def _grano() -> None:
    """Textura de grano de película (se desplaza cada frame; mucho más rápido que generarla en el navegador)."""
    destino = PUBLIC / "sfx" / "grano.png"
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        ejecutar(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=gray:s=512x512,noise=alls=60:allf=t",
                  "-frames:v", "1", str(destino)])


def _whoosh() -> None:
    destino = PUBLIC / "sfx" / "whoosh.wav"
    if destino.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    ejecutar(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=0.9:c=pink:a=0.5",
              "-af", "highpass=f=250,lowpass=f=4000,afade=t=in:d=0.4:curve=exp,afade=t=out:st=0.4:d=0.5,volume=0.8",
              "-ar", "44100", str(destino)])


def _preparar_clip(origen: Path, d: float, ancho: int, alto: int, fps: int, destino: Path) -> None:
    """Recorta/repite el clip a la duración exacta y a la resolución final (render más rápido y estable)."""
    ejecutar(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(origen), "-t", f"{d + 0.6:.2f}",
              "-vf", f"scale={ancho}:{alto}:force_original_aspect_ratio=increase,crop={ancho}:{alto},fps={fps},setsar=1",
              "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(destino)])


def _preparar_foto(origen: Path, destino: Path) -> None:
    ejecutar(["ffmpeg", "-y", "-i", str(origen), "-vf", "scale='min(2400,iw)':-2", "-q:v", "3", str(destino)])


def _render(composicion: str, props: dict, carpeta: Path, salida: Path) -> None:
    archivo = carpeta / "props.json"
    archivo.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    salida.parent.mkdir(parents=True, exist_ok=True)
    ejecutar(["node", "render.mjs", composicion, str(archivo), str(salida.resolve())], cwd=EDITOR, mostrar=True)


def renderizar(escenas: list[dict], cfg: dict, ancho: int, alto: int, nombre: str, salida: Path) -> dict:
    """Crea el video. Devuelve duración, créditos de fotos y proporción de escenas sin visual propio."""
    fps = cfg["video"]["fps"]
    vertical = alto > ancho
    rel = f"trabajo/{nombre}"
    carpeta = PUBLIC / rel
    shutil.rmtree(carpeta, ignore_errors=True)
    carpeta.mkdir(parents=True)
    _whoosh()
    _grano()

    # 1) narración escena por escena
    segmentos, duraciones = [], []
    for i, e in enumerate(escenas):
        print(f"  Voz {i + 1}/{len(escenas)}")
        voz = narrar(e["narracion"], cfg)
        seg = carpeta / f"a{i:03d}.wav"
        pausa = PAUSA_TARJETA if e["tipo"] in TARJETAS else PAUSA
        ejecutar(["ffmpeg", "-y", "-i", str(voz), "-af", f"apad=pad_dur={pausa}", "-ar", "44100", "-ac", "2", str(seg)])
        segmentos.append(seg)
        duraciones.append(duracion(seg))
    (carpeta / "audios.txt").write_text("".join(f"file '{p.name}'\n" for p in segmentos))
    ejecutar(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(carpeta / "audios.txt"), "-c", "copy",
              str(carpeta / "narracion.wav")])

    # subtítulos palabra por palabra, escena por escena (con el texto del guion como guía)
    print("  Sincronizando subtítulos...")
    palabras, t = [], 0.0
    for e, seg, d in zip(escenas, segmentos, duraciones):
        palabras += palabras_con_tiempos(seg, cfg["canal"]["idioma"], e["narracion"], t)
        t += d
    for p in segmentos:
        p.unlink()

    # 2) visuales
    usados: set = set()
    creditos, sin_visual = [], 0
    escenas_props, anterior, t = [], None, 0.0
    for i, (e, d) in enumerate(zip(escenas, duraciones)):
        print(f"  Visual {i + 1}/{len(escenas)}: [{e['fuente']}] {e['busqueda']}")
        v = obtener_visual(e["fuente"], e["busqueda"], vertical, usados) if e["busqueda"] else None
        if v is None:
            sin_visual += 1
            if anterior is None:
                raise RuntimeError(f"Sin material visual para '{e['busqueda']}'. ¿Configuraste PEXELS_API_KEY?")
            fondo = anterior  # reutiliza el último visual en vez de un fondo vacío
        else:
            origen = Path(v["ruta"])
            if origen.suffix == ".mp4":
                fondo = f"{rel}/v{i:03d}.mp4"
                _preparar_clip(origen, d, ancho, alto, fps, PUBLIC / fondo)
            else:
                fondo = f"{rel}/f{i:03d}.jpg"
                _preparar_foto(origen, PUBLIC / fondo)
            if v["credito"] and v["credito"] not in creditos:
                creditos.append(v["credito"])
        anterior = fondo
        tipo = e["tipo"]
        if tipo == "foto" and fondo.endswith(".mp4"):
            tipo = "broll"
        escenas_props.append({
            "tipo": tipo, "inicio": round(t, 3), "duracion": round(d, 3), "fondo": fondo,
            "texto": e.get("texto", ""), "subtexto": e.get("subtexto", ""), "etiqueta": e.get("etiqueta", ""),
            "credito": (v or {}).get("credito", "") if tipo == "foto" else "",
        })
        t += d

    # 3) música
    musica = None
    canciones = [p for p in MUSICA.glob("*") if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg")]
    if canciones:
        cancion = random.choice(canciones)
        shutil.copy(cancion, carpeta / f"musica{cancion.suffix.lower()}")
        musica = f"{rel}/musica{cancion.suffix.lower()}"

    props = {
        "ancho": ancho, "alto": alto, "fps": fps, "duracion": round(t, 3),
        "narracion": f"{rel}/narracion.wav", "musica": musica, "volumenMusica": cfg["video"]["volumen_musica"],
        "escenas": escenas_props, "palabras": palabras, "colorAcento": cfg["video"]["color_acento"],
        "subtitulos": cfg["video"]["subtitulos"], "idioma": cfg["canal"]["idioma"],
    }
    print(f"  Renderizando {t / 60:.1f} min...")
    _render("Documental", props, carpeta, salida)
    shutil.rmtree(carpeta, ignore_errors=True)
    return {"duracion": t, "creditos": creditos, "sin_visual": sin_visual / max(1, len(escenas))}


def miniatura(m: dict, cfg: dict, nombre: str, salida: Path) -> list[str]:
    """Renderiza la miniatura 1280x720. Devuelve los créditos de la imagen usada."""
    rel = f"trabajo/{nombre}-mini"
    carpeta = PUBLIC / rel
    carpeta.mkdir(parents=True, exist_ok=True)
    v = obtener_visual(m["fuente"], m["busqueda"], False, set())
    if v is None:
        raise RuntimeError("No se encontró imagen para la miniatura.")
    origen = Path(v["ruta"])
    imagen = carpeta / "fondo.jpg"
    if origen.suffix == ".mp4":
        subprocess.run(["ffmpeg", "-y", "-ss", "2", "-i", str(origen), "-frames:v", "1", "-q:v", "2", str(imagen)],
                       capture_output=True, check=True)
    else:
        _preparar_foto(origen, imagen)
    props = {"imagen": f"{rel}/fondo.jpg", "texto": m["texto"], "etiqueta": m.get("etiqueta", ""),
             "acento": cfg["video"]["color_acento"]}
    _render("Miniatura", props, carpeta, salida)
    shutil.rmtree(carpeta, ignore_errors=True)
    return [v["credito"]] if v["credito"] else []
