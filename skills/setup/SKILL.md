---
name: setup
description: Use this skill to set up, install, or configure the faceless-agent plugin — the onboarding that checks and prepares every dependency needed to build faceless documentaries. Trigger when the user says "setup", "configurá el plugin", "instalá las dependencias", "qué necesito para empezar", "onboarding", "preparar el entorno", "faceless setup", or runs this after installing the plugin for the first time. Detects the OS (macOS/Linux/Windows), offers to install the free system tools, and guides the paid API keys with their real cost.
---

# Setup — onboarding de faceless-agent

Prepará todo lo que hace falta para armar un documental faceless. No instales nada a ciegas:
por cada dependencia mostrá una **ficha** (qué es · para qué la usamos · cómo se obtiene · qué
cuesta) y recién ahí ofrecé instalar o guiar. Pedí permiso antes de cada instalación.

## 1. Diagnóstico

Corré el doctor y leé el JSON:
```bash
uv run python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" --human
```
Devuelve `os`, `tools` (cada una con `ok`/`ruta`, node además con `version`) y `keys`.
Usá `os` para elegir el gestor correcto en el paso siguiente.

## 2. Tipo A — herramientas de sistema (gratis, se instalan)

Para cada `tool` con `ok:false`, mostrá su ficha y ofrecé instalarla (**preguntá primero**).
Comando según el `os` que reportó el doctor:

| Herramienta | Para qué la usamos | macOS (brew) | Linux | Windows |
|---|---|---|---|---|
| **ffmpeg** / **ffprobe** | Cortar, mezclar audio y muxear el video final | `brew install ffmpeg` | `sudo apt install ffmpeg` | `winget install Gyan.FFmpeg` |
| **node** (≥22) | Correr HyperFrames (arma y renderiza el video) | `brew install node` | `sudo apt install nodejs` | `winget install OpenJS.NodeJS` |
| **uv** | Correr los scripts Python y traer faster-whisper sin instalarlo fijo | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| **git** | Actualizar el plugin / HyperFrames | `brew install git` | `sudo apt install git` | `winget install Git.Git` |

- **node**: si `tools.node.ok` es false pero `version` no es null, está instalado pero es **viejo** (<22). Avisá que hay que actualizarlo, no reinstalar desde cero.
- Después de instalar, **volvé a correr el doctor** para confirmar que quedó en verde.

### HyperFrames (motor de video) y su chequeo propio
HyperFrames se corre con `npx` (no requiere instalación global). Verificá su entorno con:
```bash
npx hyperframes doctor
```
Necesita Node ≥22, ffmpeg y Chrome/Chromium (lo instala solo la primera vez). Si falla, seguí
lo que indique su propio doctor.

## 3. Tipo B — cuentas y API keys (con billing, NO se instalan: se configuran)

Estas NO se pueden automatizar. Mostrá la ficha con el **costo real** (baja la fricción) y guiá
con el link. Después de que el usuario cargue la key, verificá con el doctor.

- **Gemini API (imágenes — nanobanana).** Con esto **creamos las imágenes** de cada escena.
  No es suscripción mensual: activás *billing* en Google AI Studio (hay que poner tarjeta) y
  pagás **por uso** (centavos por imagen). El free tier de imágenes es 0, así que el billing es
  obligatorio. Link: https://aistudio.google.com/ → API keys. Guardá la key como
  `GEMINI_API_KEY` en el `.env` del proyecto o en el entorno.

- **kie.ai (imágenes/video — opcional).** Con esto generamos los **momentos "hero" en video**
  (2-3 por documental) cuando querés movimiento real, no solo Ken Burns. Creás cuenta → API key →
  cargás saldo. Pago **por uso** ($0.30–2 por clip vs. centavos la imagen). Key: `KIE_API_KEY`.
  Si `keys.kie.ok` es false, no bloquees: el documental funciona 100% con imágenes.

- **HeyGen (música y SFX).** Con esto **ponemos la música y los efectos de sonido**. Login por
  OAuth (no es una key en `.env`):
  ```bash
  npx hyperframes auth login
  ```
  Verificá con `npx hyperframes auth status`. Revisá su tier gratuito antes de asumir costo.

- **YouTube Data API (subida automática — OPCIONAL, no recomendada para empezar).** Sirve para
  subir el video solo. El setup es pesado (proyecto en Google Cloud + OAuth + **publicar la app**;
  si queda en "Testing" los tokens mueren a los ~7 días). Por esa fricción, **dejá la subida a
  mano por defecto**: el plugin te deja el `.mp4` y la portada listos, y subís desde el navegador.

## 4. Cierre

Cuando `tools` esté en verde y las keys mínimas (Gemini + HeyGen) configuradas, avisá que está
listo y que puede arrancar un documental con el skill **nuevo-documental** ("armemos un caso").
