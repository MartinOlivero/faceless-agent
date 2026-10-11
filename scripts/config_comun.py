#!/usr/bin/env python3
"""
config_comun.py — Vocabulario de configuración del plugin y carga de `--config`.

Vive acá y no dentro de cada motor para que las tres piezas (largo, short, audio) compartan
UNA sola lista de claves válidas. Si se duplicara, tarde o temprano una quedaría vieja y el
usuario tendría una clave que funciona en un script y en otro no.

Analogía: es el diccionario del idioma que hablan los config.json. Si escribís una palabra que
no está en el diccionario, te avisa en vez de asentir y hacer otra cosa.
"""
import json
import sys
from pathlib import Path

# Todas las claves que un config.json puede traer, en cualquiera de los tres motores.
VOCABULARIO = {
    # --- Marca del canal (~/.faceless/brand.json, lo escribe el skill brand-setup) ---
    "TITULO", "ACENTO", "FUENTE_TITULO", "FUENTE_MONO",
    "SUB_TAMANO", "SUB_TAMANO_SHORT",
    "CRT_OP", "VIG_OP", "GLITCH", "GLITCH_A", "GLITCH_B",
    "OUTRO", "CTA",
    # --- Timing del caso, video largo ---
    "ESCENAS_INICIO", "KEN_BURNS", "GLITCH_EXTRA", "CALLOUTS",
    # --- Timing del caso, short vertical ---
    "SHORT_ESCENAS", "KB", "CTA_DUR",
    # --- Banda sonora ---
    "MUSICA", "SFX",
}


def aplicar_config(g: dict) -> bool:
    """Aplica cada `--config archivo.json` sobre las constantes del módulo llamador.

    Devuelve True si hubo al menos un `--config` (lo usa mezclar_audio para saber que lo
    explícito le gana a un `audio.json` implícito del proyecto).

    Pasale `globals()`. Se puede repetir y se aplican EN ORDEN, así que lo normal es
    `--config brand.json --config config.json`: primero el look del canal (permanente),
    después el timing de este video. Sin `--config` quedan los valores demo.

    Corta si aparece una clave que no está en el VOCABULARIO: sin este chequeo un typo
    (ESCENAS_INICIOS con S de más) entraría como variable nueva, nadie la leería, y el video
    saldría con los valores demo SIN UN SOLO AVISO — el error más caro de diagnosticar.

    Las claves que SÍ están en el vocabulario pero no las usa este motor se ignoran a
    propósito: `brand.json` es compartido y cada script usa su subconjunto.
    """
    hubo = False
    while "--config" in sys.argv:
        i = sys.argv.index("--config")
        ruta = Path(sys.argv[i + 1]).resolve()
        cfg = json.load(open(ruta))
        del sys.argv[i:i + 2]
        desconocidas = sorted(k for k in cfg if k not in VOCABULARIO)
        if desconocidas:
            sys.exit(f"{ruta.name}: clave(s) que no existen: {', '.join(desconocidas)}\n"
                     f"Válidas: {', '.join(sorted(VOCABULARIO))}")
        g.update({k: v for k, v in cfg.items() if k in g})
        hubo = True
    return hubo


def autotest() -> None:
    """Chequeo de las tres reglas: pisa lo suyo, ignora lo del otro motor, corta con un typo."""
    import tempfile
    g = {"ACENTO": "#7dffb4", "ESCENAS_INICIO": [0.0]}
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "c.json"

        # 1. pisa una constante propia
        p.write_text(json.dumps({"ACENTO": "#ff3366"}))
        sys.argv = ["x", "--config", str(p)]
        aplicar_config(g)
        assert g["ACENTO"] == "#ff3366", "no pisó una clave propia"
        assert sys.argv == ["x"], "no limpió --config de sys.argv"

        # 2. una clave del otro motor no rompe ni se cuela
        p.write_text(json.dumps({"SHORT_ESCENAS": [["a.png", 0]]}))
        sys.argv = ["x", "--config", str(p)]
        aplicar_config(g)
        assert "SHORT_ESCENAS" not in g, "se coló una clave que este motor no usa"

        # 3. un typo corta (esto es lo que antes pasaba en silencio)
        p.write_text(json.dumps({"ESCENAS_INICIOS": [0.0, 5.0]}))
        sys.argv = ["x", "--config", str(p)]
        try:
            aplicar_config(g)
        except SystemExit as e:
            assert "ESCENAS_INICIOS" in str(e), f"el mensaje no nombra la clave mala: {e}"
        else:
            raise AssertionError("un typo en el config NO cortó (la aspereza volvió)")
    print("autotest config_comun OK: pisa lo propio · ignora lo ajeno · corta con typo")


if __name__ == "__main__":
    autotest()
