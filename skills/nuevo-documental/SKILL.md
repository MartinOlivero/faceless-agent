---
name: nuevo-documental
description: Use this skill to create a faceless documentary video from a script and a recorded voice — the full pipeline of the faceless-agent plugin. Trigger when the user says "armemos un caso", "nuevo documental", "hagamos un video faceless", "new faceless documentary", "armá el video del caso", "convertí esta voz en documental", or wants to turn a narrated script into a cinematic short doc plus its vertical short. Orchestrates: script by scenes, voice mastering, transcription, AI images, motion+effects assembly, render, audio mix, and a matching vertical short. Requires the plugin to be set up first (see the setup skill).
---

# Nuevo documental (faceless-agent)

Convierte **guion + voz grabada** en un documental faceless cinematográfico (largo) y su
**short vertical**. Todos los scripts viven en `${CLAUDE_PLUGIN_ROOT}/scripts/`. El HTML del video
lo arma HyperFrames; el audio se mezcla aparte con ffmpeg (por eso el video sale mudo primero).

Antes de empezar, confirmá que el entorno está listo (skill **setup** / `doctor.py`) y que existe
`~/.faceless/brand.json` (skill **brand-setup**). Si no existe, corré brand-setup primero: sin eso
el video sale con la marca demo y se ve como el canal de otro. Trabajá dentro de una carpeta de
proyecto, ej. `~/faceless/<caso>/` con una subcarpeta `assets/`.

## 1. Elegir el caso y escribir el guion
- Si el usuario no tiene tema, proponé 3-5 casos con potencial (si está vidIQ, investigá
  breakout/keywords/outliers del nicho). Que elija.
- Escribí el guion **por escenas** (una idea visual por escena). Contá como thriller, no como
  tutorial. El usuario **graba su voz** leyendo el guion y te pasa el `.wav`/`.mp3`.

## 2. Masterizar la voz (a -14 LUFS)
La voz cruda hay que emparejarla al estándar de YouTube. Si está instalado el plugin
**tapemaster**, usalo ("masterizá esta voz"). Si no, ffmpeg directo:
```bash
ffmpeg -i voz.wav -af "loudnorm=I=-14:TP=-1.5:LRA=11" voz_master.wav
```

## 3. Transcribir (tiempos por palabra)
```bash
uv run --with faster-whisper python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcribir.py" \
  voz_master.wav <carpeta_proyecto>
```
Deja `<carpeta_proyecto>/transcript.json` (segmentos con `inicio/fin/texto/palabras`).
Si la voz no está en español, agregá el modelo y el idioma al final: `... <carpeta_proyecto> medium en`.

Avisale al usuario que **esto tarda**: el modelo por defecto (`medium`) procesa unos 4 minutos de
voz en ~10 minutos de CPU, y la primera vez además baja ~1,5 GB de modelo. Corrélo en background.
Para una prueba rápida podés pasarle `small` como cuarto argumento (menos preciso con nombres
propios y números, que es justo lo que más aparece en un documental — para el video final, `medium`).

## 4. Generar las imágenes (una por escena)
Con **nanobanana** (Gemini), 16:9, estilo: *"cinematic film still, dark thriller documentary,
photorealistic, no text, no people"* (adaptá al caso). Guardá una por escena en
`<carpeta_proyecto>/assets/` como `escena1.png`, `escena2.png`, … **en orden**. Debe haber
tantas imágenes como tiempos en `ESCENAS_INICIO` del config (paso 5).
- Opcional (kie.ai): 2-3 escenas "hero" en video generado para dar movimiento real. El resto,
  imagen + Ken Burns.

## 5. Escribir el `config.json` del proyecto
Los scripts traen valores demo (piloto Stuxnet). Para ESTE caso, escribí
`<carpeta_proyecto>/config.json` con las claves que correspondan (los nombres deben coincidir
**exactos** con las constantes de los scripts). Ejemplo:
```json
{
  "ESCENAS_INICIO": [0.0, 24.0, 46.0, 73.0],
  "KEN_BURNS": [[[1.15,0,0],[1.32,-70,-40]], [[1.30,-60,30],[1.12,40,-20]],
                [[1.12,50,30],[1.30,-50,-30]], [[1.32,0,-45],[1.14,0,35]]],
  "GLITCH_EXTRA": [1],
  "CALLOUTS": [[48.0, "NATANZ · IRÁN — 2010"], [61.0, "\"AIR GAP\": RED AISLADA"]],
  "MUSICA": [["acto1.mp3", 0.0, 80.0, 0.18], ["acto2.mp3", 73.0, 999.0, 0.20]],
  "SFX": [["riser.mp3", 0.3, 0.40], ["impact.mp3", 46.0, 0.55]]
}
```
- `ESCENAS_INICIO`: segundo en que entra cada imagen (mirá el `transcript.json` para clavarlo al guion).
- `KEN_BURNS`: por escena, `[[escala,x,y] inicial, [escala,x,y] final]`. Más rango = más movimiento.
- `GLITCH_EXTRA`: índices (0-based) de escenas con pulso extra de glitch.
- `CALLOUTS`: `[segundo, "texto"]` — placas de dato tipo terminal.
- `MUSICA`: `["archivo", inicio, fin, volumen]` — el archivo va en `assets/bgm/`. `999` = hasta el final.
- `SFX`: `["archivo", segundo, volumen]` — el archivo va en `assets/sfx/`.

## 6. Armar el visual (HTML de HyperFrames)
```bash
uv run python3 "${CLAUDE_PLUGIN_ROOT}/scripts/armar_video_hf.py" \
  <carpeta_proyecto> <carpeta_proyecto>/transcript.json voz_master.wav \
  --config ~/.faceless/brand.json --config <carpeta_proyecto>/config.json
```
Genera `<carpeta_proyecto>/index.html` (solo imagen + efectos + subtítulos, sin audio).

## 7. Renderizar con HyperFrames
Desde la carpeta del proyecto (ver el skill **hyperframes-cli** para detalle):
```bash
cd <carpeta_proyecto>
npx hyperframes lint && npx hyperframes check
npx hyperframes snapshot --at 5,30,60   # revisá el contact-sheet antes de render
npx hyperframes render --quality high    # sale un .mp4 MUDO
```

## 8. Bajar música/SFX y mezclar el audio
- Traé las pistas de música y efectos (HeyGen, vía el skill **media-use** de HyperFrames) y dejalas en
  `<carpeta_proyecto>/assets/bgm/` y `assets/sfx/` con los nombres que pusiste en el config.
- Mezclá voz + música + SFX sobre el video mudo:
```bash
uv run python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mezclar_audio.py" \
  <video_mudo.mp4> voz_master.wav <carpeta_proyecto>/assets <salida_final.mp4> \
  --config <carpeta_proyecto>/config.json
```
Sale a ~-14 LUFS (estándar YouTube). Ese `<salida_final.mp4>` es el documental terminado.

## 9. Short vertical (opcional pero recomendado)
Recorta el gancho de la voz (~45s) y armá el 9:16 reusando las imágenes:
```bash
ffmpeg -i voz_master.wav -t 45 gancho.wav
uv run python3 "${CLAUDE_PLUGIN_ROOT}/scripts/armar_short_hf.py" \
  <carpeta_short> <carpeta_proyecto>/transcript.json gancho.wav \
  --config ~/.faceless/brand.json --config <carpeta_short>/config_short.json
```
El `config_short.json` usa las claves `SHORT_ESCENAS` (`["escena1.png", segundo]`), `KB` (Ken
Burns por plano) y `CTA_DUR`. Renderizá con HyperFrames y mezclá el audio del gancho igual que
el largo. Las imágenes del short pueden ser un symlink a las del largo (`assets` → `../<caso>/assets`).

## 10. Portada y entrega
- Portada con **nanobanana pro** (Gemini 3 Pro escribe texto en español), 16:9 → redimensioná a
  1280x720 JPEG: `ffmpeg -i portada.png -vf scale=1280:720 portada.jpg`.
- Entregá los `.mp4` + la portada. **Subida a mano por defecto** (la automática es opcional y
  frágil, ver skill setup). Si el usuario insiste en automatizarla, se hace con la API de YouTube
  v3 (`videos.insert` resumible) y su propio proyecto de Google Cloud — no hay atajo.

Estrategia (recordar al usuario): el **short capta** (Reels/Shorts/TikTok) y cierra con CTA al
largo; el **largo monetiza** (RPM alto). Guion + voz humanos; la IA solo produce (blindaje
anti-demonetización). Disclosure de IA en la descripción.
