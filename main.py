"""Canal automático de YouTube: documentales de historias reales.

Uso:
  python main.py auto                 # siguiente tema -> investigación -> guion -> video + short -> miniatura -> subir
  python main.py auto --sin-subir     # igual, pero deja los archivos en /salida para revisarlos
  python main.py guiones 5            # investiga y escribe 5 guiones por adelantado (API de Claude)
  python main.py ideas 20             # añade 20 temas nuevos a temas.txt (API de Claude)
  python main.py render guiones/x.json [--sin-short]
  python main.py autorizar            # una sola vez: conecta tu canal de YouTube
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from canal.util import GUIONES, RAIZ, SALIDA, cargar_config, slug

def _cargar_secretos() -> None:
    """Lee secretos/.env (no se sube a git) como variables de entorno, sin pisar las ya definidas."""
    archivo = RAIZ / "secretos" / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_cargar_secretos()
TEMAS = RAIZ / "temas.txt"
ESTADO = RAIZ / "estado.json"
MAX_SIN_VISUAL = 0.25  # si más del 25% de escenas no tuvo material propio, no se sube


def leer_estado() -> dict:
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {"hechos": [], "ultima_fecha": None, "videos": []}


def guardar_estado(estado: dict) -> None:
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def cola_temas(estado: dict) -> list[str]:
    if not TEMAS.exists():
        return []
    temas = [t.strip() for t in TEMAS.read_text(encoding="utf-8").splitlines()]
    return [t for t in temas if t and not t.startswith("#") and slug(t) not in estado["hechos"]]


def hay_claude() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def obtener_guion(tema: str, cfg: dict) -> dict:
    from canal.guion import cargar_guion, generar_guion, guardar_guion

    ruta = GUIONES / f"{slug(tema)}.json"
    if ruta.exists():
        print(f"Usando guion existente: {ruta.name}")
        return cargar_guion(ruta)
    if not hay_claude():
        raise SystemExit(f"No hay guion para '{tema}' ni ANTHROPIC_API_KEY. Pídeselo a Claude o configura la clave.")
    print(f"Guion nuevo con Claude: {tema}")
    guion = generar_guion(tema, cfg)
    print(f"  Guardado en {guardar_guion(guion).name}")
    return guion


def _descripcion(texto: str, fuentes: list[str], creditos: list[str]) -> str:
    partes = [texto.strip()]
    if fuentes:
        partes.append("Sources:\n" + "\n".join(f"- {f}" for f in fuentes))
    if creditos:
        partes.append("Footage and image credits:\n" + "\n".join(f"- {c}" for c in creditos))
    return "\n\n".join(partes)


def producir(guion: dict, cfg: dict, con_short: bool = True) -> Path:
    from canal.montaje import miniatura, renderizar

    nombre = slug(guion["tema"])
    carpeta = SALIDA / nombre
    v = cfg["video"]
    print(f"Video largo ({len(guion['escenas'])} escenas)")
    largo = renderizar(guion["escenas"], cfg, v["ancho"], v["alto"], nombre, carpeta / "video.mp4")
    print("Miniatura")
    creditos_mini = miniatura(guion["miniatura"], cfg, nombre, carpeta / "miniatura.jpg")
    meta = {
        "tema": guion["tema"], "titulo": guion["titulo"], "etiquetas": guion["etiquetas"],
        "descripcion": _descripcion(guion["descripcion"], guion["fuentes"], largo["creditos"] + creditos_mini),
        "resumen_es": guion["resumen_es"], "duracion_min": round(largo["duracion"] / 60, 1),
        "sin_visual": round(largo["sin_visual"], 2),
    }
    if con_short and cfg["short"]["activar"] and guion.get("short", {}).get("escenas"):
        s, sh = cfg["short"], guion["short"]
        print(f"Short ({len(sh['escenas'])} escenas)")
        corto = renderizar(sh["escenas"], cfg, s["ancho"], s["alto"], nombre + "-short", carpeta / "short.mp4")
        meta["short"] = {"titulo": sh["titulo"], "descripcion": _descripcion(sh["descripcion"], [], corto["creditos"])}
    (carpeta / "metadatos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo: {carpeta} ({meta['duracion_min']} min)")
    return carpeta


def fecha_publicacion(estado: dict, cfg: dict) -> date:
    manana = datetime.now(ZoneInfo(cfg["youtube"]["zona_horaria"])).date() + timedelta(days=1)
    if estado.get("ultima_fecha"):
        return max(manana, date.fromisoformat(estado["ultima_fecha"]) + timedelta(days=1))
    return manana


def publicar(carpeta: Path, cfg: dict, estado: dict) -> bool:
    from canal import subir

    meta = json.loads((carpeta / "metadatos.json").read_text(encoding="utf-8"))
    if meta["sin_visual"] > MAX_SIN_VISUAL:
        print(f"NO se sube: al {meta['sin_visual']:.0%} de las escenas les faltó material visual propio.")
        return False
    if not subir.disponible():
        print("YouTube no está conectado (falta el token). Revisa el README, paso 'Conectar YouTube'.")
        return False
    yt = cfg["youtube"]
    cuando_largo = cuando_short = None
    if yt["programar"]:
        dia = fecha_publicacion(estado, cfg)
        h, m = map(int, yt["hora_publicacion"].split(":"))
        cuando_largo = datetime.combine(dia, time(h, m), ZoneInfo(yt["zona_horaria"]))
        cuando_short = cuando_largo + timedelta(hours=4)
        estado["ultima_fecha"] = dia.isoformat()
        print(f"Programado para {cuando_largo:%Y-%m-%d %H:%M} ({yt['zona_horaria']})")

    registro = {"tema": meta["tema"], "fecha": estado.get("ultima_fecha")}
    registro["video_id"] = subir.subir_video(carpeta / "video.mp4", meta["titulo"], meta["descripcion"], meta["etiquetas"],
                                             cfg, miniatura=carpeta / "miniatura.jpg", publicar_en=cuando_largo)
    if (carpeta / "short.mp4").exists():
        s = meta["short"]
        enlace = f"\n\nFull story: https://youtu.be/{registro['video_id']}"
        registro["short_id"] = subir.subir_video(carpeta / "short.mp4", s["titulo"], s["descripcion"] + enlace,
                                                 meta["etiquetas"], cfg, publicar_en=cuando_short)
    estado.setdefault("videos", []).append(registro)
    return True


def cmd_auto(args, cfg):
    estado = leer_estado()
    cola = cola_temas(estado)
    if len(cola) < 3 and hay_claude():
        cmd_ideas(argparse.Namespace(n=15), cfg)
        cola = cola_temas(estado)
    if not cola:
        raise SystemExit("No quedan temas en temas.txt.")
    for tema in cola[: args.n]:
        print(f"\n=== {tema} ===")
        guion = obtener_guion(tema, cfg)
        carpeta = producir(guion, cfg)
        if args.sin_subir or not cfg["youtube"]["subir"]:
            continue  # prueba: el tema sigue en la cola
        if not publicar(carpeta, cfg, estado):
            sys.exit(1)  # el tema queda en la cola para reintentarlo
        estado["hechos"].append(slug(tema))
        guardar_estado(estado)


def cmd_guiones(args, cfg):
    for tema in cola_temas(leer_estado())[: args.n]:
        obtener_guion(tema, cfg)


def cmd_ideas(args, cfg):
    from canal.ideas import generar_ideas

    estado = leer_estado()
    nuevas = generar_ideas(args.n, cola_temas(estado) + estado["hechos"], cfg)
    with open(TEMAS, "a", encoding="utf-8") as f:
        f.write("".join(f"{t}\n" for t in nuevas))
    print(f"Añadidos {len(nuevas)} temas a temas.txt")


def cmd_render(args, cfg):
    from canal.guion import cargar_guion

    producir(cargar_guion(Path(args.guion)), cfg, con_short=not args.sin_short)


def main():
    p = argparse.ArgumentParser(description="Canal automático de YouTube")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("auto")
    a.add_argument("--n", type=int, default=1, help="cuántos videos producir")
    a.add_argument("--sin-subir", action="store_true")
    sub.add_parser("guiones").add_argument("n", type=int, nargs="?", default=3)
    sub.add_parser("ideas").add_argument("n", type=int, nargs="?", default=15)
    r = sub.add_parser("render")
    r.add_argument("guion")
    r.add_argument("--sin-short", action="store_true")
    sub.add_parser("autorizar")
    args = p.parse_args()

    cfg = cargar_config()
    if args.cmd == "autorizar":
        from canal.subir import autorizar
        autorizar()
    else:
        {"auto": cmd_auto, "guiones": cmd_guiones, "ideas": cmd_ideas, "render": cmd_render}[args.cmd](args, cfg)


if __name__ == "__main__":
    sys.exit(main())
