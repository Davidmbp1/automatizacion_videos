"""Material visual gratuito y con licencia comercial.

- stock: clips de video de Pixabay (PIXABAY_API_KEY) y, si tienes clave, Pexels (PEXELS_API_KEY).
- archivo: fotos reales de personas, lugares y empresas en Wikimedia Commons (sin clave, licencias CC/PD).
"""
import hashlib
import html
import json
import os
import re
from pathlib import Path

import time

import requests

from .util import CACHE

UA = {"User-Agent": "automatizacion-videos/1.0 (https://github.com/Davidmbp1/automatizacion_videos)"}
LICENCIAS_OK = ("cc0", "public domain", "pd", "cc by", "cc-by")  # incluye CC BY-SA; excluye NC/ND


def _descargar(url: str, destino: Path, headers: dict | None = None) -> Path:
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=180, headers=headers or UA) as r:
            r.raise_for_status()
            tmp = destino.with_suffix(".part")
            with open(tmp, "wb") as f:
                for trozo in r.iter_content(1 << 20):
                    f.write(trozo)
            tmp.rename(destino)
    return destino


def _pexels(consulta: str, vertical: bool, usados: set) -> dict | None:
    clave = os.environ.get("PEXELS_API_KEY")
    if not clave:
        return None
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": clave},
                     params={"query": consulta, "per_page": 20, "orientation": "portrait" if vertical else "landscape"},
                     timeout=30)
    if r.status_code != 200:
        return None
    for video in r.json().get("videos", []):
        if f"px{video['id']}" in usados or video.get("duration", 0) < 4:
            continue
        archivos = [f for f in video["video_files"] if f.get("file_type") == "video/mp4" and f.get("height")]
        archivos = [f for f in archivos if min(f["width"], f["height"]) <= 1080] or archivos
        if not archivos:
            continue
        mejor = max(archivos, key=lambda f: f["width"] * f["height"])
        usados.add(f"px{video['id']}")
        ruta = _descargar(mejor["link"], CACHE / "medios" / f"pexels-{video['id']}.mp4")
        return {"ruta": ruta, "credito": "Pexels"}
    return None


def _api_pixabay(ruta: str, params: dict) -> dict | None:
    """Consulta la API de Pixabay guardando la respuesta 24 h (lo exige su licencia de uso)."""
    clave = os.environ.get("PIXABAY_API_KEY")
    if not clave:
        return None
    id_cache = hashlib.sha1(json.dumps([ruta, params], sort_keys=True).encode()).hexdigest()[:16]
    cache = CACHE / "api" / f"pixabay-{id_cache}.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < 86400:
        return json.loads(cache.read_text())
    r = requests.get(f"https://pixabay.com/api/{ruta}", params={"key": clave, "safesearch": "true", **params}, timeout=30)
    if r.status_code == 429:
        time.sleep(int(r.headers.get("X-RateLimit-Reset", "30")) + 1)
        r = requests.get(f"https://pixabay.com/api/{ruta}", params={"key": clave, "safesearch": "true", **params}, timeout=30)
    if r.status_code != 200:
        return None
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(r.text)
    return r.json()


def _pixabay(consulta: str, vertical: bool, usados: set) -> dict | None:
    datos = _api_pixabay("videos/", {"q": consulta[:100], "per_page": 30, "video_type": "film"})
    for video in (datos or {}).get("hits", []):
        if f"pb{video['id']}" in usados or video.get("duration", 0) < 4:
            continue
        # la versión más grande que no pase de 1080p (las de 4K pesan demasiado)
        versiones = [v for v in video["videos"].values() if v.get("url") and v.get("width")]
        buenas = [v for v in versiones if max(v["width"], v["height"]) <= 2000] or versiones
        if not buenas:
            continue
        mejor = max(buenas, key=lambda v: v["width"] * v["height"])
        if min(mejor["width"], mejor["height"]) < 700:
            continue
        usados.add(f"pb{video['id']}")
        return {"ruta": _descargar(mejor["url"], CACHE / "medios" / f"pixabay-{video['id']}.mp4"), "credito": "Pixabay"}
    return None


def _pixabay_foto(consulta: str, vertical: bool, usados: set) -> dict | None:
    datos = _api_pixabay("", {"q": consulta[:100], "per_page": 30, "image_type": "photo",
                              "orientation": "vertical" if vertical else "horizontal", "min_width": 1280})
    for img in (datos or {}).get("hits", []):
        if f"pbi{img['id']}" in usados:
            continue
        usados.add(f"pbi{img['id']}")
        url = img.get("fullHDURL") or img["largeImageURL"]
        return {"ruta": _descargar(url, CACHE / "medios" / f"pixabay-img-{img['id']}.jpg"), "credito": "Pixabay"}
    return None


def _wikimedia(consulta: str, usados: set) -> dict | None:
    params = {
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {consulta}",
        "gsrnamespace": 6, "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1920,
    }
    datos = None
    for espera in (0, 5, 15, 30):  # Wikimedia limita las consultas seguidas: reintenta con pausa
        time.sleep(espera or 1)
        r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=30, params=params)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
            datos = r.json()
            break
    if datos is None:
        return None
    paginas = sorted(datos.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for p in paginas:
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        licencia = meta.get("LicenseShortName", {}).get("value", "")
        if p["title"] in usados or ii.get("width", 0) < 900 or not licencia.lower().startswith(LICENCIAS_OK) \
                or any(x in licencia.lower() for x in ("nc", "nd")):
            continue
        autor = re.sub(r"<[^>]+>", "", html.unescape(meta.get("Artist", {}).get("value", ""))).strip()[:60]
        url = ii.get("thumburl") or ii.get("url")
        ext = ".png" if url.lower().split("?")[0].endswith(".png") else ".jpg"
        usados.add(p["title"])
        ruta = _descargar(url, CACHE / "medios" / f"wm-{hashlib.sha1(url.encode()).hexdigest()[:12]}{ext}")
        credito = f"{autor} · {licencia} · Wikimedia Commons" if autor else f"{licencia} · Wikimedia Commons"
        return {"ruta": ruta, "credito": credito}
    return None


def _simplificar(consulta: str) -> str:
    palabras = consulta.split()
    return " ".join(palabras[:2]) if len(palabras) > 2 else consulta


def obtener_visual(fuente: str, consulta: str, vertical: bool, usados: set) -> dict | None:
    """Devuelve {"ruta", "credito"} o None si no se encontró nada."""
    stock = lambda q: _pexels(q, vertical, usados) or _pixabay(q, vertical, usados)
    if fuente == "archivo":
        # personas y lugares reales: solo Wikimedia; si falla, un clip genérico (nunca una foto equivocada)
        orden = [lambda: _wikimedia(consulta, usados), lambda: stock(consulta), lambda: stock(_simplificar(consulta))]
    else:
        orden = [lambda: stock(consulta), lambda: stock(_simplificar(consulta)),
                 lambda: _pixabay_foto(consulta, vertical, usados)]
    for intento in orden:
        try:
            r = intento()
            if r:
                return r
        except requests.RequestException as e:
            print(f"  Búsqueda falló: {e}")
    return None
