#!/usr/bin/env python3
"""
Chequeo mínimo de la pieza no trivial del plugin: que `--config file.json` PISE las constantes
del módulo (lo que hace reusable el motor para cualquier caso, no solo el demo Stuxnet).
Corré: uv run python3 tests/test_config.py   (o: uv run --with pytest pytest)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import armar_video_hf as v  # noqa: E402


def test_config_pisa_constantes(tmp_path: Path):
    tmp_config = tmp_path / "config.json"
    v.ESCENAS_INICIO = [0.0, 24.0]  # valor demo cualquiera
    tmp_config.write_text(json.dumps({"ESCENAS_INICIO": [0.0, 5.0, 10.0]}))
    sys.argv = ["armar_video_hf.py", "proyecto", "t.json", "voz.wav",
                "--config", str(tmp_config)]
    v.aplicar_config()
    assert v.ESCENAS_INICIO == [0.0, 5.0, 10.0], "el --config no pisó ESCENAS_INICIO"
    # y dejó los argumentos posicionales intactos (sin --config)
    assert sys.argv == ["armar_video_hf.py", "proyecto", "t.json", "voz.wav"], \
        "no limpió --config de sys.argv"


def test_marca_y_caso_en_orden(tmp_path: Path):
    """`--config brand.json --config config.json`: se aplican en orden y la marca llega al HTML."""
    brand, caso = tmp_path / "brand.json", tmp_path / "caso.json"
    brand.write_text(json.dumps({"ACENTO": "#ff3366", "GLITCH": 0, "OUTRO": []}))
    caso.write_text(json.dumps({"ESCENAS_INICIO": [0.0, 5.0]}))
    sys.argv = ["armar_video_hf.py", "p", "t.json", "v.wav",
                "--config", str(brand), "--config", str(caso)]
    v.aplicar_config()
    assert v.ACENTO == "#ff3366" and v.ESCENAS_INICIO == [0.0, 5.0], "no aplicó los dos configs"

    html = v.ensamblar_html(60.0, {
        "clips": [], "subs": [], "callouts": [], "tw_img": [], "tw_sub": [], "tw_call": [],
        "tw_global": v.tweens_globales(60.0), "tw_outro": v.construir_outro(60.0),
        "outro_html": v.outro_html(60.0),
    })
    assert "#ff3366" in html, "el acento de la marca no llegó al CSS"
    assert "#7dffb4" not in html, "quedó color demo hardcodeado en el HTML"
    assert 'id="outro"' not in html, 'OUTRO: [] debería dejar el video sin el div de cierre'
    assert "opacity:0.0," in html or "opacity:0," in html, "GLITCH: 0 debería apagar el glitch"


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        test_config_pisa_constantes(Path(d))
        print("OK: --config pisa las constantes y limpia sys.argv")
        test_marca_y_caso_en_orden(Path(d))
        print("OK: marca + caso se aplican en orden y la marca llega al HTML")
