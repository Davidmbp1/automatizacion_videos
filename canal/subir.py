"""Subida a YouTube con la YouTube Data API v3 (gratuita, ~6 subidas al día con la cuota por defecto)."""
import json
import os
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .util import RAIZ

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
SECRETOS = RAIZ / "secretos"
TOKEN = SECRETOS / "token.json"
CLIENTE = SECRETOS / "client_secret.json"


def autorizar() -> None:
    """Paso único en tu PC: abre el navegador para dar permiso a tu canal."""
    if not CLIENTE.exists():
        raise SystemExit(f"Falta {CLIENTE}. Descárgalo de Google Cloud Console (ver README).")
    flujo = InstalledAppFlow.from_client_secrets_file(str(CLIENTE), SCOPES)
    cred = flujo.run_local_server(port=0, prompt="consent", access_type="offline")
    TOKEN.write_text(cred.to_json())
    print(f"Listo. Token guardado en {TOKEN}")
    print("Para GitHub Actions, copia TODO el contenido de ese archivo al secreto YT_TOKEN_JSON.")


def _credenciales() -> Credentials | None:
    if os.environ.get("YT_TOKEN_JSON"):
        info = json.loads(os.environ["YT_TOKEN_JSON"])
    elif TOKEN.exists():
        info = json.loads(TOKEN.read_text())
    else:
        return None
    cred = Credentials.from_authorized_user_info(info, SCOPES)
    if not cred.valid and cred.refresh_token:
        cred.refresh(Request())
    return cred


def disponible() -> bool:
    return _credenciales() is not None


def subir_video(video: Path, titulo: str, descripcion: str, etiquetas: list[str], cfg: dict,
                miniatura: Path | None = None, publicar_en: datetime | None = None) -> str:
    yt_cfg = cfg["youtube"]
    youtube = build("youtube", "v3", credentials=_credenciales(), cache_discovery=False)
    estado = {
        "privacyStatus": "private" if publicar_en else yt_cfg["privacidad"],
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": yt_cfg["contenido_sintetico"],
    }
    if publicar_en:
        estado["publishAt"] = publicar_en.isoformat()
    cuerpo = {
        "snippet": {
            "title": titulo[:100],
            "description": descripcion[:5000],
            "tags": etiquetas[:30],
            "categoryId": yt_cfg["categoria_id"],
            "defaultLanguage": cfg["canal"]["idioma"],
            "defaultAudioLanguage": cfg["canal"]["idioma"],
        },
        "status": estado,
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    peticion = youtube.videos().insert(part="snippet,status", body=cuerpo, media_body=media)
    respuesta = None
    while respuesta is None:
        progreso, respuesta = peticion.next_chunk()
        if progreso:
            print(f"  Subiendo... {int(progreso.progress() * 100)}%")
    video_id = respuesta["id"]
    print(f"  Subido: https://youtu.be/{video_id}")

    if miniatura and miniatura.exists():
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(miniatura))).execute()
        except HttpError as e:
            print(f"  No se pudo poner la miniatura (¿canal sin verificar por teléfono?): {e.reason}")
    return video_id
