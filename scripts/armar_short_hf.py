#!/usr/bin/env python3
"""
armar_short_hf.py — Arma un Short/Reel VERTICAL (9:16) de HyperFrames a partir del
gancho de un caso: reusa las imágenes 16:9 (recortadas al centro), subtítulos grandes
centrados y un CTA final al canal.

El audio (voz del gancho + música + SFX) se mezcla aparte con ffmpeg.

Uso:
  uv run python3 armar_short_hf.py <carpeta_proyecto> <transcript.json> <gancho.wav>
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # para correrlo por ruta absoluta
import config_comun  # noqa: E402

W, H = 1080, 1920
CTA_DUR = 4.0  # segundos de CTA extra después de la voz

# ---- MARCA (misma que el largo; se pisa con `--config brand.json`, ver skill brand-setup) ----
ACENTO = "#7dffb4"
FUENTE_TITULO = "'Arial Black', Inter, sans-serif"
FUENTE_MONO = "'Courier New', monospace"
SUB_TAMANO_SHORT = 74                                    # px del subtítulo vertical
CRT_OP = 0.45
VIG_OP = 0.55
GLITCH = 1.0
GLITCH_A = "rgba(255,0,60,.35)"
GLITCH_B = "rgba(0,200,255,.35)"
CTA = ["▶ EL CASO COMPLETO", "EN MI CANAL · SEGUIME"]

# Qué imagen se ve y desde qué segundo (reordenadas para acompañar el gancho).
SHORT_ESCENAS = [
    ("escena1.png", 0.0),    # las máquinas destruyéndose
    ("escena5.png", 11.0),   # chispas / se rompen
    ("escena2.png", 24.0),   # "¿cómo un archivo?" -> código
    ("escena6.png", 37.0),   # "¿quién fue capaz?" -> dossier/Estado
]
KB = [
    ((1.25, 60, 0), (1.40, -60, 0)),
    ((1.40, -50, 20), (1.22, 50, -20)),
    ((1.22, 40, 0), (1.40, -40, 0)),
    ((1.40, 0, 30), (1.24, 0, -30)),
]


def dur(wav: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", str(wav)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def construir_imagenes(assets: Path, voz_fin: float, total: float):
    clips, tw = [], []
    n = len(SHORT_ESCENAS)
    for i, (img, ini) in enumerate(SHORT_ESCENAS):
        prox = SHORT_ESCENAS[i + 1][1] if i + 1 < n else total
        d = round((prox - ini) + (0.8 if i + 1 < n else 0), 3)
        clips.append(f'    <section class="clip esc" id="esc{i}" data-start="{ini}" '
                     f'data-duration="{d}" data-track-index="{i}">'
                     f'<img class="kb" id="img{i}" src="assets/{img}" /></section>')
        (s0, x0, y0), (s1, x1, y1) = KB[i]
        tw.append(f'  tl.fromTo("#img{i}", {{scale:{s0}, x:{x0}, y:{y0}}}, '
                  f'{{scale:{s1}, x:{x1}, y:{y1}, ease:"none", duration:{d}}}, {ini});')
        if i > 0:
            tw.append(f'  tl.fromTo("#esc{i}", {{opacity:0}}, {{opacity:1, duration:0.6, ease:"power1.out"}}, {ini});')
        if i + 1 < n:
            tw.append(f'  tl.to("#esc{i}", {{opacity:0, duration:0.8, ease:"power1.in"}}, {round(prox-0.05,3)})'
                      f'.set("#esc{i}", {{opacity:0}}, {round(ini+d,3)});')
    return clips, tw


def construir_subs(segs: list, voz_fin: float):
    subs, tw = [], []
    vis = [s for s in segs if float(s["inicio"]) < voz_fin - 0.5]
    for j, s in enumerate(vis):
        ini = round(float(s["inicio"]), 3)
        prox = float(vis[j + 1]["inicio"]) if j + 1 < len(vis) else voz_fin
        d = round(max(prox - ini - 0.05, 0.4), 3)
        subs.append(f'    <div class="clip sub" id="sub{j}" data-start="{ini}" '
                    f'data-duration="{d}" data-track-index="20">{esc(s["texto"])}</div>')
        tw.append(f'  tl.fromTo("#sub{j}", {{opacity:0, y:26}}, {{opacity:1, y:0, duration:0.22, ease:"power2.out"}}, {ini})'
                  f'.to("#sub{j}", {{opacity:0, duration:0.22, ease:"power2.in"}}, {round(ini+d-0.22,3)})'
                  f'.set("#sub{j}", {{opacity:0}}, {round(prox,3)});')
    return subs, tw


def glitch_js(total: float) -> str:
    g = GLITCH  # 0 = sin glitch
    L = ['  function gl(T){',
         f'    tl.fromTo("#glr", {{opacity:{0.5*g}, x:{-40*g}}}, {{opacity:0, x:-6, duration:0.3, ease:"power2.out", immediateRender:false}}, T);',
         f'    tl.fromTo("#glb", {{opacity:{0.5*g}, x:{40*g}}}, {{opacity:0, x:6, duration:0.3, ease:"power2.out", immediateRender:false}}, T);',
         f'    tl.fromTo("#stage", {{y:{-12*g}}}, {{y:0, duration:0.3, ease:"power3.out", immediateRender:false}}, T);',
         '    tl.set("#glr", {opacity:0}, T+0.3); tl.set("#glb", {opacity:0}, T+0.3);  }']
    for _, ini in SHORT_ESCENAS[1:]:
        L.append(f'  gl({ini});')
    reps = max(2, int(total // 5))
    L.append(f'  tl.to("#vig", {{opacity:{round(VIG_OP*1.6,3)}, duration:3, ease:"sine.inOut", yoyo:true, repeat:{reps}}}, 0);')
    return "\n".join(L)


def main():
    # `--config file.json` pisa la marca y SHORT_ESCENAS/KB/CTA_DUR. Repetible y en orden:
    # `--config brand.json --config config_short.json`. Ver config_comun.py.
    config_comun.aplicar_config(globals())
    proyecto = Path(sys.argv[1]).resolve()
    segs = json.load(open(Path(sys.argv[2]).resolve()))
    voz = Path(sys.argv[3]).resolve()
    voz_fin = dur(voz)
    total = round(voz_fin + CTA_DUR, 3)

    clips, tw_img = construir_imagenes(proyecto / "assets", voz_fin, total)
    subs, tw_sub = construir_subs(segs, voz_fin)
    cta_t = round(voz_fin - 3.0, 3)
    nl = chr(10)
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  body {{ margin:0; background:#000; font-family:{FUENTE_TITULO}; }}
  #root {{ position:relative; width:{W}px; height:{H}px; overflow:hidden; background:#000; }}
  #stage {{ position:absolute; inset:0; }}
  .clip {{ position:absolute; inset:0; }}
  section.esc {{ overflow:hidden; }}
  img.kb {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; will-change:transform; }}
  #glr,#glb {{ position:absolute; inset:0; z-index:30; opacity:0; pointer-events:none; }}
  #glr {{ background:{GLITCH_A}; }} #glb {{ background:{GLITCH_B}; }}
  #vig {{ position:absolute; inset:0; z-index:27; pointer-events:none; opacity:{VIG_OP};
          background:radial-gradient(ellipse at center, transparent 42%, rgba(0,0,0,.9) 100%); }}
  #crt {{ position:absolute; inset:0; z-index:28; pointer-events:none; opacity:{CRT_OP};
          background:repeating-linear-gradient(0deg, rgba(0,0,0,.3) 0 1px, transparent 1px 3px); }}
  /* z-index 43 = por ENCIMA del velo del CTA (42), igual que en el largo. Hoy el CTA entra recién
     cuando termina la voz y no se solapan, pero si un subtítulo se estira queda gris e ilegible. */
  .sub {{ display:flex; align-items:center; justify-content:center; padding:0 70px; box-sizing:border-box;
          z-index:43; opacity:0; color:#fff; font-size:{SUB_TAMANO_SHORT}px; line-height:1.22; font-weight:800; text-align:center;
          text-shadow:0 4px 22px rgba(0,0,0,.95), 0 0 3px #000; transform:translateY(180px); }}
  #cta {{ position:absolute; inset:0; z-index:42; display:flex; flex-direction:column; align-items:center;
          justify-content:center; gap:28px; opacity:0; background:rgba(0,0,0,.86); pointer-events:none; }}
  #cta .l1 {{ font-family:{FUENTE_MONO}; color:{ACENTO}; font-size:64px; font-weight:800;
              letter-spacing:2px; text-shadow:0 0 20px {ACENTO}99; text-align:center; }}
  #cta .l2 {{ font-family:{FUENTE_MONO}; color:#fff; font-size:46px; letter-spacing:2px; text-align:center; }}
</style></head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{H}" data-duration="{total}">
    <div id="stage">
{nl.join(clips)}
    </div>
    <div id="vig"></div>
    <div id="crt"></div>
    <div id="glr"></div>
    <div id="glb"></div>
{nl.join(subs)}
    <div id="cta" class="clip" data-start="{cta_t}" data-duration="{round(total-cta_t,3)}" data-track-index="50">
      <div class="l1">{esc(CTA[0])}</div>
      <div class="l2">{esc(CTA[1])}</div>
    </div>
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
{nl.join(tw_img)}
{nl.join(tw_sub)}
{glitch_js(total)}
  tl.fromTo("#cta", {{opacity:0}}, {{opacity:1, duration:0.5, ease:"power2.out", immediateRender:false}}, {cta_t});
    window.__timelines["main"] = tl;
  </script>
</body></html>
"""
    salida = proyecto / "index.html"
    salida.write_text(html, encoding="utf-8")
    assert html.count("<img") == len(SHORT_ESCENAS), "faltan imágenes"
    print(f"OK -> {salida}  ({len(SHORT_ESCENAS)} planos | {len(subs)} subs | {total}s | {W}x{H})")


if __name__ == "__main__":
    main()
