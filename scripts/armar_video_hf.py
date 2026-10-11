#!/usr/bin/env python3
"""
armar_video_hf.py (v2) — Arma el index.html de HyperFrames para un documental faceless
con MOVIMIENTO: Ken Burns fuerte, crossfades con glitch, scanlines CRT, callouts,
RGB-split en escenas hacker y outro del canal.

El HTML se ocupa SOLO del visual (imágenes + efectos + subtítulos). El audio completo
(voz + músicas + SFX) se mezcla aparte con ffmpeg, por eso acá no va ningún <audio>.

Uso:
  uv run python3 armar_video_hf.py <carpeta_proyecto> <transcript.json> <voz.wav>
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # para correrlo por ruta absoluta
import config_comun  # noqa: E402

# ---------------------------------------------------------------------------
# MARCA — el "look" del canal. Se pisa con `--config brand.json` (ver skill brand-setup).
# Estos valores son la marca DEMO (Día Cero: thriller hacker retro). Si no los cambiás,
# tus videos van a verse como los de otro canal.
# ---------------------------------------------------------------------------
TITULO = "documental"                                    # <title> del HTML
ACENTO = "#7dffb4"                                       # callouts, outro, detalles
FUENTE_TITULO = "'Arial Black', Inter, system-ui, sans-serif"
FUENTE_MONO = "'Courier New', monospace"
SUB_TAMANO = 52                                          # px del subtítulo
CRT_OP = 0.5                                             # scanlines CRT (0 = apagado)
VIG_OP = 0.6                                             # viñeta oscura (0 = apagado)
GLITCH = 1.0                                             # fuerza del glitch (0 = sin glitch)
GLITCH_A = "rgba(255,0,60,.35)"                          # capa RGB izquierda
GLITCH_B = "rgba(0,200,255,.35)"                         # capa RGB derecha
OUTRO = ["NARRADO POR TU NOMBRE", "▶ MI CANAL: @tu.canal"]  # [] = sin outro

# En qué segundo arranca cada imagen (según el guion).
ESCENAS_INICIO = [0.0, 24.0, 46.0, 73.0, 97.0, 146.0, 179.0, 215.0]

# Ken Burns por escena: (escala,x,y) inicial -> final. Rango amplio = más movimiento.
KEN_BURNS = [
    ((1.15, 0, 0), (1.32, -70, -40)),
    ((1.30, -60, 30), (1.12, 40, -20)),
    ((1.12, 50, 30), (1.30, -50, -30)),
    ((1.32, 0, -45), (1.14, 0, 35)),
    ((1.14, -50, -20), (1.34, 60, 30)),
    ((1.30, 50, -30), (1.12, -50, 30)),
    ((1.14, 0, 35), (1.36, 0, -45)),
    ((1.18, 0, 0), (1.30, 0, 0)),
]

# Escenas hacker donde meto un pulso extra de glitch RGB a mitad del plano.
GLITCH_EXTRA = [1, 3]  # índices 0-based: escena 2 (código) y 4 (USB)

# Placas de dato (callout) que entran en momentos clave: (segundo, texto).
CALLOUTS = [
    (48.0, "NATANZ · IRÁN — 2010"),
    (61.0, '"AIR GAP": RED AISLADA'),
    (150.0, "ZERO-DAY ×4"),
    (166.0, "OPERACIÓN: JUEGOS OLÍMPICOS"),
]


def duracion_audio(wav: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(wav)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def esc(t: str) -> str:
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def listar_imagenes(assets: Path) -> list[Path]:
    return sorted(assets.glob("escena*.png"),
                  key=lambda p: int("".join(c for c in p.stem if c.isdigit())))


def construir_imagenes(imgs: list[Path], total: float) -> tuple[list[str], list[str]]:
    """Cada imagen en su propio track (para poder solaparse en el crossfade)."""
    clips, tw = [], []
    solape = 0.8
    for i, img in enumerate(imgs):
        ini = ESCENAS_INICIO[i]
        prox = ESCENAS_INICIO[i + 1] if i + 1 < len(imgs) else total
        dur = round((prox - ini) + (solape if i + 1 < len(imgs) else 0), 3)
        clips.append(
            f'    <section class="clip esc" id="esc{i}" data-start="{ini}" data-duration="{dur}" data-track-index="{i}">\n'
            f'      <img class="kb" id="img{i+1}" src="assets/{img.name}" />\n'
            f'    </section>'
        )
        (s0, x0, y0), (s1, x1, y1) = KEN_BURNS[i]
        tw.append(
            f'  tl.fromTo("#img{i+1}", {{scale:{s0}, x:{x0}, y:{y0}}}, '
            f'{{scale:{s1}, x:{x1}, y:{y1}, ease:"none", duration:{dur}}}, {ini});'
        )
        # crossfade: fade-in al entrar (menos la primera) y fade-out al final del solape
        if i > 0:
            tw.append(f'  tl.fromTo("#esc{i}", {{opacity:0}}, {{opacity:1, duration:0.7, ease:"power1.out"}}, {ini});')
        if i + 1 < len(imgs):
            fo = round(prox - 0.05, 3)
            tw.append(f'  tl.to("#esc{i}", {{opacity:0, duration:{solape}, ease:"power1.in"}}, {fo})'
                      f'.set("#esc{i}", {{opacity:0}}, {round(ini + dur, 3)});')
    return clips, tw


def construir_subtitulos(segs: list, total: float) -> tuple[list[str], list[str]]:
    subs, tw = [], []
    for j, s in enumerate(segs):
        ini = round(float(s["inicio"]), 3)
        prox = float(segs[j + 1]["inicio"]) if j + 1 < len(segs) else total
        fin_seg = s.get("fin")
        tope = round(prox - 0.05, 3)
        fin = tope if fin_seg is None else min(tope, round(float(fin_seg) + 0.6, 3))
        dur = round(fin - ini, 3)
        subs.append(
            f'    <div class="clip sub" id="sub{j}" data-start="{ini}" '
            f'data-duration="{dur}" data-track-index="20">{esc(s["texto"])}</div>'
        )
        fo = round(ini + dur - 0.25, 3)
        tw.append(
            f'  tl.fromTo("#sub{j}", {{opacity:0, y:22}}, '
            f'{{opacity:1, y:0, duration:0.25, ease:"power2.out"}}, {ini})'
            f'.to("#sub{j}", {{opacity:0, duration:0.25, ease:"power2.in"}}, {fo})'
            f'.set("#sub{j}", {{opacity:0}}, {round(prox,3)});'
        )
    return subs, tw


def construir_callouts() -> tuple[list[str], list[str]]:
    divs, tw = [], []
    for k, (t, txt) in enumerate(CALLOUTS):
        divs.append(f'    <div class="clip callout" id="call{k}" data-start="{t}" '
                    f'data-duration="4.5" data-track-index="{25+k}"><span>{esc(txt)}</span></div>')
        tw.append(
            f'  tl.fromTo("#call{k}", {{opacity:0, x:-40}}, '
            f'{{opacity:1, x:0, duration:0.4, ease:"power3.out"}}, {t})'
            f'.to("#call{k}", {{opacity:0, duration:0.4, ease:"power2.in"}}, {t+4.0})'
            f'.set("#call{k}", {{opacity:0}}, {t+4.5});'
        )
    return divs, tw


def outro_html(total: float) -> str:
    """El overlay de cierre con la marca del canal. OUTRO vacío = sin cierre."""
    if not OUTRO:
        return ""
    return (f'    <div id="outro" class="clip" data-start="{round(total - 8.0, 3)}" '
            f'data-duration="8" data-track-index="96">\n'
            f'      <div id="outro-l1">{esc(OUTRO[0])}</div>\n'
            f'      <div id="outro-l2">{esc(OUTRO[1])}</div>\n'
            f'    </div>')


def construir_outro(total: float) -> str:
    """Tweens del overlay de cierre con la marca del canal (últimos ~8s)."""
    if not OUTRO:
        return ""
    t = round(total - 8.0, 3)
    return (
        f'  tl.fromTo("#outro", {{opacity:0}}, {{opacity:1, duration:0.6, ease:"power2.out", immediateRender:false}}, {t});\n'
        f'  tl.fromTo("#outro-l1", {{opacity:0, y:30}}, {{opacity:1, y:0, duration:0.6, ease:"power3.out"}}, {t});\n'
        f'  tl.fromTo("#outro-l2", {{opacity:0, y:24}}, {{opacity:1, y:0, duration:0.6, ease:"power3.out"}}, {round(t+0.5,3)});\n'
    )


def tweens_globales(total: float) -> str:
    """Glitch en cada transición + pulsos extra + scanline sweep + vignette breathe."""
    g = GLITCH  # 0 = sin glitch (todas las opacidades y el sacudón quedan en cero)
    lineas = ["  function glitchAt(T, big){",
              "    var d = big ? 0.45 : 0.28;",
              f'    tl.set("#glx", {{opacity: (big?0.6:0.42)*{g}}}, T);',
              '    tl.to("#glx", {opacity:0, duration:d, ease:"power2.out"}, T);',
              f'    tl.fromTo("#glr", {{opacity:{0.5*g}, x:{-50*g}}}, {{opacity:0, x:-8, duration:d, ease:"power2.out", immediateRender:false}}, T);',
              f'    tl.fromTo("#glb", {{opacity:{0.5*g}, x:{50*g}}}, {{opacity:0, x:8, duration:d, ease:"power2.out", immediateRender:false}}, T);',
              f'    tl.fromTo("#stage", {{x:{-14*g}}}, {{x:0, duration:d, ease:"power3.out", immediateRender:false}}, T);',
              "  }"]
    for ini in ESCENAS_INICIO[1:]:
        lineas.append(f"  glitchAt({ini}, false);")
    # un índice de la última escena (o fuera de rango) no tiene "escena siguiente": se ignora
    for i in [i for i in GLITCH_EXTRA if 0 <= i < len(ESCENAS_INICIO) - 1]:
        mid = round(ESCENAS_INICIO[i] + (ESCENAS_INICIO[i+1] - ESCENAS_INICIO[i]) * 0.5, 3)
        lineas.append(f"  glitchAt({mid}, true);")
    # barrido de scanline (una pasada lenta) y respiración de la viñeta, deterministas
    reps = max(2, int(total // 6))
    lineas.append(f'  tl.fromTo("#scan", {{y:-1080}}, {{y:1080, duration:6, ease:"none", repeat:{reps}}}, 0);')
    lineas.append(f'  tl.to("#vig", {{opacity:{round(VIG_OP * 1.4, 3)}, duration:4, ease:"sine.inOut", yoyo:true, repeat:{reps}}}, 0);')
    return "\n".join(lineas)


def ensamblar_html(total: float, bloques: dict) -> str:
    nl = chr(10)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1920, height=1080" />
  <title>{esc(TITULO)}</title>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>
    body {{ margin:0; background:#000; font-family:{FUENTE_TITULO}; }}
    #root {{ position:relative; width:1920px; height:1080px; overflow:hidden; background:#000; }}
    #stage {{ position:absolute; inset:0; }}
    .clip {{ position:absolute; inset:0; }}
    section.esc {{ overflow:hidden; }}
    img.kb {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; will-change:transform; }}
    /* capas RGB del glitch (tinte, blending normal, arrancan invisibles) */
    #glr,#glb {{ position:absolute; inset:0; z-index:30; opacity:0; pointer-events:none; }}
    #glr {{ background:{GLITCH_A}; }}
    #glb {{ background:{GLITCH_B}; }}
    #glx {{ position:absolute; inset:0; z-index:31; opacity:0; pointer-events:none;
            background:repeating-linear-gradient(0deg, rgba(255,255,255,.08) 0 2px, transparent 2px 5px); }}
    /* scanlines CRT + barrido + viñeta */
    #crt {{ position:absolute; inset:0; z-index:28; pointer-events:none; opacity:{CRT_OP};
            background:repeating-linear-gradient(0deg, rgba(0,0,0,.28) 0 1px, transparent 1px 3px); }}
    #scan {{ position:absolute; left:0; width:1920px; height:220px; z-index:29; pointer-events:none;
             opacity:{CRT_OP};
             background:linear-gradient(to bottom, transparent, {ACENTO}14, transparent); }}
    #vig {{ position:absolute; inset:0; z-index:27; pointer-events:none; opacity:{VIG_OP};
            background:radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,.85) 100%); }}
    /* viñeta inferior para el subtítulo */
    #root::after {{ content:""; position:absolute; inset:0; pointer-events:none; z-index:26;
      background:linear-gradient(to top, rgba(0,0,0,.78) 0%, rgba(0,0,0,0) 30%); }}
    /* z-index 43 = por ENCIMA del velo del outro (42). Debajo, el velo negro al 93% dejaba el
       último subtítulo como un fantasma gris ilegible justo cuando la voz dice el CTA. Arriba se
       lee nítido sobre negro: la marca queda al centro y el cierre hablado, abajo. */
    .sub {{ display:flex; align-items:flex-end; justify-content:center; padding:0 180px 88px;
            box-sizing:border-box; z-index:43; opacity:0; color:#fff; font-size:{SUB_TAMANO}px; line-height:1.25;
            font-weight:800; text-align:center; text-shadow:0 3px 18px rgba(0,0,0,.9), 0 0 2px #000; }}
    .callout {{ display:flex; align-items:flex-start; justify-content:flex-start; padding:120px 0 0 120px;
                z-index:41; opacity:0; }}
    .callout span {{ font-family:{FUENTE_MONO}; font-weight:700; font-size:40px; color:{ACENTO};
                     letter-spacing:2px; padding:12px 22px; border-left:5px solid {ACENTO};
                     background:rgba(0,0,0,.55); text-shadow:0 0 12px {ACENTO}80; }}
    #outro {{ position:absolute; inset:0; z-index:42; display:flex; flex-direction:column;
              align-items:center; justify-content:center; gap:22px; pointer-events:none;
              opacity:0; background:rgba(0,0,0,.93); }}
    #outro-l1 {{ opacity:0; font-family:{FUENTE_MONO}; color:#fff; font-size:40px; letter-spacing:3px; }}
    #outro-l2 {{ opacity:0; font-family:{FUENTE_MONO}; color:{ACENTO}; font-size:56px; font-weight:800;
                 letter-spacing:2px; text-shadow:0 0 18px {ACENTO}99; }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{round(total,3)}">
    <div id="stage">
{nl.join(bloques['clips'])}
    </div>
    <div id="vig"></div>
    <div id="crt"></div>
    <div id="scan"></div>
    <div id="glr"></div>
    <div id="glb"></div>
    <div id="glx"></div>
{nl.join(bloques['subs'])}
{nl.join(bloques['callouts'])}
{bloques['outro_html']}
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
{nl.join(bloques['tw_img'])}
{nl.join(bloques['tw_sub'])}
{nl.join(bloques['tw_call'])}
{bloques['tw_global']}
{bloques['tw_outro']}
    window.__timelines["main"] = tl;
  </script>
</body>
</html>
"""


def aplicar_config():
    # `--config file.json` pisa las constantes de acá abajo (marca + timing del caso). Repetible
    # y en orden: `--config brand.json --config config.json`. Ver config_comun.py.
    config_comun.aplicar_config(globals())


def main():
    aplicar_config()
    proyecto = Path(sys.argv[1]).resolve()
    segs = json.load(open(Path(sys.argv[2]).resolve()))
    voz = Path(sys.argv[3]).resolve()
    total = duracion_audio(voz)

    imgs = listar_imagenes(proyecto / "assets")
    assert len(imgs) == len(ESCENAS_INICIO), f"{len(imgs)} imágenes vs {len(ESCENAS_INICIO)} tiempos"

    clips, tw_img = construir_imagenes(imgs, total)
    subs, tw_sub = construir_subtitulos(segs, total)
    calls, tw_call = construir_callouts()
    html = ensamblar_html(total, {
        "clips": clips, "subs": subs, "callouts": calls,
        "tw_img": tw_img, "tw_sub": tw_sub, "tw_call": tw_call,
        "tw_global": tweens_globales(total), "tw_outro": construir_outro(total),
        "outro_html": outro_html(total),
    })

    salida = proyecto / "index.html"
    salida.write_text(html, encoding="utf-8")
    assert html.count("<img") == len(imgs), "faltan <img>"
    assert html.count('class="clip sub"') == len(segs), "faltan subtítulos"
    print(f"OK -> {salida}")
    print(f"   {len(imgs)} imágenes | {len(segs)} subtítulos | {len(CALLOUTS)} callouts | {round(total,1)}s")


if __name__ == "__main__":
    main()
