"""Utilidades compartidas: configuración, rutas, ffmpeg."""
import json
import re
import subprocess
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GUIONES = RAIZ / "guiones"
SALIDA = RAIZ / "salida"
CACHE = RAIZ / ".cache"
MUSICA = RAIZ / "musica"
EDITOR = RAIZ / "editor"
PUBLIC = EDITOR / "public"


def cargar_config() -> dict:
    return json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))


def slug(texto: str, largo: int = 60) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto[:largo].rstrip("-") or "video"


def ejecutar(cmd: list[str], cwd: Path | None = None, mostrar: bool = False) -> None:
    """Ejecuta un comando; si falla, muestra el final de su salida de error."""
    if mostrar:
        r = subprocess.run(cmd, cwd=cwd)
        if r.returncode != 0:
            raise RuntimeError(f"Falló: {' '.join(cmd[:4])}")
        return
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"Falló: {' '.join(cmd[:6])}...\n{r.stderr[-3000:]}")


def duracion(ruta: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(ruta)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())
