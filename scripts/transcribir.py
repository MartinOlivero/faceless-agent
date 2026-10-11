#!/usr/bin/env python3
"""
transcribir.py — Convierte la voz grabada (wav/mp3) en transcript.json con tiempos por
segmento Y por palabra, que es lo que leen armar_video_hf / armar_short_hf para ubicar
subtítulos y sincronizar las escenas.

Usa faster-whisper. NO lo tengas instalado fijo: corré este script con uv inyectándolo:
  uv run --with faster-whisper python3 transcribir.py <voz.wav> <carpeta_salida> [modelo] [idioma]

Deja en <carpeta_salida>:
  - transcript.json  -> [{inicio, fin, texto, palabras:[{palabra,inicio,fin}]}, ...]
  - transcript.txt   -> lectura rápida con marcas [mm:ss]
"""
import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel  # se inyecta con `uv run --with faster-whisper`


def mmss(seg: float) -> str:
    return f"{int(seg // 60):02d}:{int(seg % 60):02d}"


def main():
    if len(sys.argv) < 3:
        sys.exit("uso: transcribir.py <voz.wav> <carpeta_salida> [modelo=medium] [idioma=es]")
    audio = Path(sys.argv[1]).resolve()
    salida = Path(sys.argv[2]).resolve()
    modelo = sys.argv[3] if len(sys.argv) > 3 else "medium"
    idioma = sys.argv[4] if len(sys.argv) > 4 else "es"   # código ISO: es, en, pt...
    salida.mkdir(parents=True, exist_ok=True)

    print(f"Transcribiendo '{audio.name}' con faster-whisper ('{modelo}', idioma '{idioma}')... puede tardar.")
    model = WhisperModel(modelo, device="cpu", compute_type="int8")
    segmentos_iter, _ = model.transcribe(str(audio), language=idioma,
                                         word_timestamps=True, vad_filter=True)

    segmentos, lineas_txt = [], []
    for seg in segmentos_iter:
        palabras = [
            {"palabra": (w.word or "").strip(), "inicio": round(w.start, 3), "fin": round(w.end, 3)}
            for w in (seg.words or []) if (w.word or "").strip()
        ]
        segmentos.append({
            "inicio": round(seg.start, 3),
            "fin": round(seg.end, 3),
            "texto": seg.text.strip(),
            "palabras": palabras,
        })
        lineas_txt.append(f"[{mmss(seg.start)}] {seg.text.strip()}")
        print(f"   {mmss(seg.start)}  {seg.text.strip()[:70]}")

    (salida / "transcript.json").write_text(
        json.dumps(segmentos, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "transcript.txt").write_text("\n".join(lineas_txt), encoding="utf-8")
    assert segmentos, "no se detectó habla en el audio"
    print(f"OK -> {salida/'transcript.json'}  ({len(segmentos)} segmentos)")


if __name__ == "__main__":
    main()
