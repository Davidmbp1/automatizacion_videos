# Ledger Noir: canal automático de documentales de crímenes financieros reales

Este sistema produce documentales para YouTube con historias reales de dinero, negocios y tecnología: fraudes, hackeos, empresas que subieron y cayeron. Funciona solo, en GitHub Actions. **No necesitas instalar nada en tu PC.**

```
tema → investigación web con fuentes (Claude) → guion de documental
     → voz natural (Kokoro / Chatterbox) → subtítulos palabra por palabra (Whisper)
     → clips de Pixabay + fotos reales de Wikimedia
     → edición con Remotion (movimiento de cámara, capítulos, cifras animadas, citas, rótulos, grano, música, efectos)
     → miniatura de diseño → video largo + short → subida programada a YouTube
```

| Pieza | Herramienta | Costo |
|---|---|---|
| Investigación y guion | Claude (búsqueda web + escritura) | Lo único que se paga |
| Voz | Kokoro (Apache 2.0) o Chatterbox (MIT, clona voces) | Gratis |
| Subtítulos sincronizados | faster-whisper (MIT) | Gratis |
| Clips y fotos | Pixabay API + Wikimedia Commons | Gratis |
| Edición | Remotion (gratis para personas individuales) | Gratis |
| Ejecución diaria | GitHub Actions (repositorio público = minutos ilimitados) | Gratis |
| Subida | YouTube Data API v3 | Gratis |

## Por qué este nicho y este idioma

- **Negocios y finanzas es la categoría que mejor paga por vista.** El público de EE. UU. paga varias veces más que el hispano: lee los rangos en las fuentes de abajo.
- **El formato documental de historias** retiene mucho más que las explicaciones genéricas, y cada video es original, investigado y con fuentes. Eso protege la monetización frente a la política de "contenido repetitivo".
- **Las voces gratuitas suenan mucho más humanas en inglés.** Si prefieres español, cambia `"idioma": "es"` en `config.json` y usa el motor `chatterbox`, que tiene un modelo oficial para español latino.

## Pasos que te tocan (todo en el navegador)

### 1. Secretos del repositorio

En GitHub, entra a **Settings → Secrets and variables → Actions → New repository secret** y crea:

| Nombre | Valor |
|---|---|
| `PIXABAY_API_KEY` | Tu clave de Pixabay |
| `ANTHROPIC_API_KEY` | Clave de https://console.anthropic.com (para que Claude investigue y escriba solo) |
| `YT_TOKEN_JSON` | Ver el paso 3 |

### 2. Probar sin subir nada

Ve a **Actions → Producir video → Run workflow**.
- Escribe en "guion": `guiones/el-hackeo-de-twitter-de-2020-un-chico-de-17-anos-de-florida.json`
- Deja "Subir a YouTube" sin marcar.

Al terminar (unos 60 a 90 minutos), descarga el video en **Artifacts**, al final de la página de la ejecución.

### 3. Conectar YouTube sin instalar nada (OAuth Playground)

1. Entra a https://console.cloud.google.com y crea un proyecto.
2. **APIs y servicios → Biblioteca → YouTube Data API v3 → Habilitar**.
3. **Pantalla de consentimiento de OAuth**: tipo Externo; agrega tu correo como usuario de prueba y luego pulsa **Publicar app**. Si la dejas en modo de prueba, el permiso caduca a los 7 días.
4. **Credenciales → Crear → ID de cliente de OAuth → Aplicación web**. En "URI de redireccionamiento autorizados" agrega `https://developers.google.com/oauthplayground`. Guarda el *Client ID* y el *Client secret*.
5. Abre https://developers.google.com/oauthplayground:
   - Pulsa el engranaje ⚙️, marca **Use your own OAuth credentials** y pega el ID y el secreto.
   - A la izquierda, escribe `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube` y pulsa **Authorize APIs**. Elige tu canal y acepta.
   - Pulsa **Exchange authorization code for tokens** y copia el **Refresh token**.
6. Crea el secreto `YT_TOKEN_JSON` con este contenido, poniendo tus datos:
   ```json
   {"client_id": "TU_CLIENT_ID", "client_secret": "TU_CLIENT_SECRET", "refresh_token": "TU_REFRESH_TOKEN"}
   ```

> Los videos subidos desde un proyecto de API sin auditar quedan **privados**. Al inicio eso conviene: revisas cada video en YouTube Studio y lo programas con dos clics. Para que se publiquen solos, pide la auditoría gratuita: https://support.google.com/youtube/contact/yt_api_form

### 4. Música (opcional)

Sube a la carpeta `musica/` entre 5 y 10 pistas instrumentales de la **Biblioteca de audio de YouTube** que digan "No se requiere atribución". Elige un estilo documental o de suspenso.

## Uso diario

- **Automático:** cada día a las 11:23 UTC se produce el siguiente tema de `temas.txt` y se programa en YouTube.
- **Revisión:** cada guion incluye `resumen_es` (un resumen en español) y su archivo `.notas.md` con las fuentes, en `guiones/`.
- **Guiones escritos por Claude en Claude Code:** pídeme "escribe el guion del siguiente tema". Así no gastas API.

## Ajustes (`config.json`)

- `voz.kokoro_voz`: `am_michael` (narrador de EE. UU.), `bm_george` (británico, estilo documental), `af_heart` (mujer).
- `voz.motor`: `kokoro` (rápido), `chatterbox` (más humano, clona la voz de `chatterbox_referencia`, unas 4 veces más lento) o `edge`.
- `video.color_acento`, `youtube.hora_publicacion`, `youtube.zona_horaria`.

## Reglas para conservar la monetización

- Un video largo al día como máximo. Al inicio, 3 a 4 por semana.
- Revisa el `resumen_es` y las fuentes antes de publicar.
- Responde comentarios y fija uno en cada video.
- El sistema **no sube** videos a los que les falte material visual en más del 25 % de las escenas.

## Estructura

```
main.py                 comandos (auto, render, guiones, ideas, autorizar)
config.json             ajustes del canal
temas.txt               cola de historias
guiones/                guiones JSON + notas de investigación
canal/guion.py          investigación web + guion (Claude)
canal/voz.py            Kokoro / Chatterbox / Edge
canal/alinear.py        tiempos por palabra (Whisper)
canal/medios.py         Pixabay / Pexels / Wikimedia
canal/montaje.py        prepara todo y llama al editor
canal/subir.py          YouTube Data API
editor/                 Remotion: plantillas de video y miniatura
```

Fuentes de los datos de RPM: [outlierkit](https://outlierkit.com/blog/youtube-rpm-finance-niche), [overseeros](https://www.overseeros.com/blog/youtube-rpm-by-niche), [tubeanalytics](https://tubeanalytics.net/benchmarks/spain), [lenostube](https://www.lenostube.com/en/youtube-cpm-rpm-rates/).
