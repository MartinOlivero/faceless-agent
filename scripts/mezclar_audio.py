#!/usr/bin/env python3
"""
mezclar_audio.py — Pega la banda sonora completa sobre el video visual de HyperFrames.

El video de HyperFrames sale SIN audio (solo imagen + efectos). Este script arma con
ffmpeg la mezcla final: tu voz al frente + 3 músicas que cambian por acto + efectos de
sonido en cada transición/golpe, y lo muxea con el video.

Analogía: el video es la película muda; esto es la sala de sonido que le pone la voz,
la música y los golpes, todo a su volumen justo.

Uso:
  uv run python3 mezclar_audio.py <video_visual.mp4> <voz.wav> <carpeta_assets> <salida.mp4>
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # para correrlo por ruta absoluta
import config_comun  # noqa: E402

# Música por acto: (archivo en assets/bgm, segundo de inicio, segundo de fin, volumen).
# Se loopea sola para cubrir su ventana; con fade de entrada/salida para el crossfade.
MUSICA = [
    ("acto1.mp3", 0.0, 80.0, 0.18),
    ("acto2.mp3", 73.0, 185.0, 0.18),
    ("acto3.mp3", 175.0, 999.0, 0.20),   # 999 = hasta el final (se recorta al total)
]

# Efectos: (archivo en assets/sfx, segundo, volumen). Alineados a transiciones y golpes.
SFX = [
    ("cinematic-riser-build-up-tension.mp3", 0.3, 0.40),
    ("deep-cinematic-impact-boom-hit.mp3", 8.5, 0.55),
    ("deep-cinematic-impact-boom-hit.mp3", 99.0, 0.55),
    ("digital-glitch-distortion.mp3", 24.0, 0.50),
    ("digital-glitch-distortion.mp3", 73.0, 0.50),
    ("digital-glitch-distortion.mp3", 146.0, 0.50),
    ("whoosh-transition-swoosh.mp3", 46.0, 0.35),
    ("whoosh-transition-swoosh.mp3", 97.0, 0.35),
    ("whoosh-transition-swoosh.mp3", 179.0, 0.35),
    ("whoosh-transition-swoosh.mp3", 215.0, 0.40),
    ("computer-terminal-beep-data.mp3", 30.0, 0.30),
    ("computer-terminal-beep-data.mp3", 61.0, 0.30),
]


def duracion(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _existe(archivo: Path):
    """Corta con un mensaje que se entiende, en vez de dejar que ffmpeg escupa su error."""
    if not archivo.is_file():
        sys.exit(f"ERROR: falta {archivo}. Revisá MUSICA y SFX en el config de ESTE video: "
                 "si no los declarás, se usan los del video de demostración.")


def construir_comando(video: Path, voz: Path, assets: Path, salida: Path) -> list[str]:
    # El largo lo marca el VIDEO, no la voz: el short tiene unos segundos de CTA después de
    # que la voz termina, y midiendo la voz esos segundos se cortaban del archivo final.
    total = duracion(video)
    cmd = ["ffmpeg", "-y", "-i", str(video)]          # input 0 = video (sin audio)
    filtros, labels = [], []

    # input 1 = voz (al frente). El aformat NO es decorativo: amix adopta el layout del primer
    # input, y como la voz suele grabarse en mono, sin esto toda la música estéreo se aplasta a
    # un solo canal y el documental pierde el ancho. Subir la voz a estéreo arrastra la mezcla.
    cmd += ["-i", str(voz)]
    # apad rellena con silencio hasta el final del video: la mezcla dura lo que dura la primera pista.
    filtros.append(f"[1:a]volume=1.0,aformat=channel_layouts=stereo,apad=whole_dur={total}[v]")
    labels.append("[v]")

    idx = 2  # próximo índice de input
    for k, (arch, t0, t1, vol) in enumerate(MUSICA):
        if t0 >= total:
            continue                      # esa música arranca después de que el video terminó
        _existe(assets / "bgm" / arch)
        fin = min(t1, total)
        vent = round(fin - t0, 3)
        cmd += ["-stream_loop", "-1", "-i", str(assets / "bgm" / arch)]  # loop infinito
        d0 = int(t0 * 1000)
        filtros.append(
            f"[{idx}:a]atrim=0:{vent},volume={vol},"
            f"afade=t=in:st=0:d=2,afade=t=out:st={max(0.0, round(vent-4,3))}:d=4,"
            f"adelay={d0}|{d0}[m{k}]")
        labels.append(f"[m{k}]")
        idx += 1

    for k, (arch, t, vol) in enumerate(SFX):
        if t >= total:
            continue
        _existe(assets / "sfx" / arch)
        cmd += ["-i", str(assets / "sfx" / arch)]
        d = int(t * 1000)
        filtros.append(f"[{idx}:a]volume={vol},adelay={d}|{d}[s{k}]")
        labels.append(f"[s{k}]")
        idx += 1

    n = len(labels)
    # El loudnorm final es lo que hace verdadera la promesa de "-14 LUFS, estándar YouTube".
    # Sin él la mezcla queda a merced de cuán fuerte hayas grabado la voz: si no la masterizaste
    # antes, el video sale fuera de norma. TP=-1.5 deja aire para que la recompresión de YouTube
    # no clipee (llegar a -0.1 dBTP es pedirle problemas).
    filtros.append(f"{''.join(labels)}amix=inputs={n}:duration=first:normalize=0,"
                   f"loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    cmd += ["-filter_complex", ";".join(filtros),
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(salida)]
    return cmd


def main():
    # `--config file.json` pisa MUSICA y SFX por proyecto. Ver config_comun.py.
    config_comun.aplicar_config(globals())
    video, voz, assets, salida = (Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(),
                                  Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve())
    cmd = construir_comando(video, voz, assets, salida)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        sys.exit(f"ffmpeg falló (código {r.returncode})")
    assert salida.exists() and salida.stat().st_size > 0, "no se generó la salida"
    print(f"OK -> {salida}  ({round(duracion(salida),1)}s)")


if __name__ == "__main__":
    main()
