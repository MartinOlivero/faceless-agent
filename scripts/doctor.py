#!/usr/bin/env python3
"""
doctor.py — Chequeo de dependencias del plugin faceless-agent. Imprime JSON con el estado
de cada cosa que hace falta para armar un documental. NO instala nada: solo mira y reporta;
el skill /setup lee este JSON y ofrece instalar/guiar lo que falte.

Analogía: es la lucecita del tablero del auto. No arregla el motor, te dice qué está en rojo.

Uso:
  python3 doctor.py            # imprime JSON
  python3 doctor.py --human    # además, resumen legible
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# --- Tipo A: herramientas de sistema (gratis, instalables) ---
HERRAMIENTAS = ["ffmpeg", "ffprobe", "node", "uv", "python3", "git"]

# --- Tipo B: cuentas/keys con billing (no se instalan, se configuran) ---
# Nombres de variable de entorno donde suele vivir cada key.
KEYS = {
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],   # nanobanana / imágenes
    "kie": ["KIE_API_KEY", "KIE_AI_API_KEY"],          # imágenes/video kie.ai
}


def version_node() -> str | None:
    """Devuelve la versión de node ('v24.1.0') o None si no está."""
    if not shutil.which("node"):
        return None
    try:
        return subprocess.run(["node", "--version"], capture_output=True, text=True,
                              timeout=10).stdout.strip() or None
    except Exception:
        return None


def node_ok(v: str | None) -> bool:
    """HyperFrames pide Node >= 22."""
    if not v:
        return False
    try:
        return int(v.lstrip("v").split(".")[0]) >= 22
    except ValueError:
        return False


def env_de_dotenv() -> dict:
    """Junta las variables de los .env que encuentre, para no depender solo del entorno del shell.

    Mira, en orden: el directorio actual, cada carpeta padre hasta la raíz, y `~/.faceless/.env`.
    Buscar SOLO en el directorio actual daba un falso negativo garantizado, porque el flujo normal
    es trabajar dentro de la carpeta del video (`~/faceless/<caso>/`) mientras el `.env` con las
    keys vive más arriba, en la carpeta del canal. El usuario veía "falta la key" con la key puesta.

    Gana el .env más cercano al directorio actual: lo específico del proyecto pisa lo general.
    """
    valores = {}
    candidatos = [Path.home() / ".faceless" / ".env"]
    candidatos += [p / ".env" for p in reversed([Path.cwd(), *Path.cwd().parents])]
    for f in candidatos:                       # de lo general a lo específico: el último gana
        if not f.is_file():
            continue
        for linea in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, _, val = linea.partition("=")
                valores[k.strip()] = val.strip().strip('"').strip("'")
    return valores


def key_presente(nombres: list, dotenv: dict) -> bool:
    return any(os.environ.get(n) or dotenv.get(n) for n in nombres)


def diagnosticar() -> dict:
    dotenv = env_de_dotenv()
    nver = version_node()
    tools = {}
    for t in HERRAMIENTAS:
        ruta = shutil.which(t)
        tools[t] = {"ok": bool(ruta), "ruta": ruta}
    tools["node"]["version"] = nver
    tools["node"]["ok"] = node_ok(nver)  # ok = existe Y es >= 22

    keys = {nombre: {"ok": key_presente(vars_, dotenv), "vars": vars_}
            for nombre, vars_ in KEYS.items()}

    return {
        "os": platform.system(),          # Darwin / Linux / Windows
        "tools": tools,
        "keys": keys,
        # HeyGen (música/SFX) y HyperFrames no se chequean acá: se verifican con su propio CLI
        # (`npx hyperframes doctor` y `npx hyperframes auth status`). El skill /setup los corre.
        "notas": {
            "heygen": "verificar con: npx hyperframes auth status",
            "hyperframes": "verificar con: npx hyperframes doctor",
        },
    }


def main():
    d = diagnosticar()
    print(json.dumps(d, ensure_ascii=False, indent=2))
    if "--human" in sys.argv:
        print("\n--- resumen ---", file=sys.stderr)
        for t, info in d["tools"].items():
            v = f" ({info.get('version')})" if info.get("version") else ""
            print(f"  {'✓' if info['ok'] else '✗'} {t}{v}", file=sys.stderr)
        for k, info in d["keys"].items():
            print(f"  {'✓' if info['ok'] else '✗'} key {k}", file=sys.stderr)


if __name__ == "__main__":
    main()
