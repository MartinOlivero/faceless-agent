---
name: brand-setup
description: Use this skill to define the visual identity (brand) of the user's faceless channel — accent color, fonts, subtitle size, CRT/glitch/vignette intensity, outro and short CTA — and write it to a reusable brand.json. Trigger when the user says "configurá mi marca", "brand setup", "quiero que se vea como mi canal", "cambiar los colores del video", "sacar el glitch", "que no se vea retro", "personalizar el look", "my videos look like someone else's channel", or is setting up the faceless-agent plugin for the first time. Run this ONCE per channel, before the first documentary.
---

# Brand setup (faceless-agent)

El plugin viene con la marca **demo** (Día Cero: thriller hacker retro — verde fósforo, scanlines
CRT, glitch RGB). Si el usuario no la cambia, **sus videos van a verse como los de otro canal**.

Este skill entrevista al usuario y escribe **un solo archivo**: `~/.faceless/brand.json`. Ese
archivo se le pasa a los dos motores con `--config` ANTES del config del caso, así el look es
permanente y el timing es por video.

## 1. Entrevistar (corto, 5 preguntas)

No preguntes de a una cosa por vez como un formulario. Proponé una opción por defecto en cada
punto y que el usuario corrija lo que no le guste. Preguntas:

1. **Nicho y tono** — ¿de qué son los videos y qué sensación querés? (thriller, true crime,
   divulgación calmada, negocios, historia). De acá sale todo lo demás.
2. **Color de acento** — el color de los datos en pantalla y del cierre. Hex `#rrggbb`.
   *Tiene que ser claro y saturado: va sobre negro.* Si el usuario da un color oscuro, avisale
   y proponé una versión más clara.
3. **Fuentes** — una de título/subtítulos y una monoespaciada para las placas de dato.
4. **Intensidad del efecto retro** — scanlines CRT, glitch y viñeta: ¿fuerte, sutil o nada?
5. **Textos de cierre** — las 2 líneas del outro del largo y las 2 del CTA del short.

## 2. Elegir fuentes que existan en cualquier máquina

HyperFrames renderiza en un navegador headless: **si la fuente no está instalada, cae en una
por defecto y el video sale distinto en cada máquina.** Salvo que el usuario tenga una fuente
propia instalada y la quiera, usá uno de estos stacks (existen en macOS, Windows y Linux):

| Tono | Título / subtítulos | Monoespaciada |
|---|---|---|
| Impacto, thriller | `'Arial Black', Inter, system-ui, sans-serif` | `'Courier New', monospace` |
| Editorial, documental | `Georgia, 'Times New Roman', serif` | `'Courier New', monospace` |
| Limpio, moderno | `'Helvetica Neue', Arial, system-ui, sans-serif` | `'SF Mono', Consolas, monospace` |

## 3. Escribir `~/.faceless/brand.json`

Todas las claves son opcionales: lo que no pongas queda en el valor demo. Los nombres deben
coincidir **exactos** (son las constantes de los scripts).

```json
{
  "TITULO": "Mi Canal",
  "ACENTO": "#7dffb4",
  "FUENTE_TITULO": "'Arial Black', Inter, system-ui, sans-serif",
  "FUENTE_MONO": "'Courier New', monospace",
  "SUB_TAMANO": 52,
  "SUB_TAMANO_SHORT": 74,
  "CRT_OP": 0.5,
  "VIG_OP": 0.6,
  "GLITCH": 1.0,
  "GLITCH_A": "rgba(255,0,60,.35)",
  "GLITCH_B": "rgba(0,200,255,.35)",
  "OUTRO": ["NARRADO POR TU NOMBRE", "▶ MI CANAL: @tu.canal"],
  "CTA": ["▶ EL CASO COMPLETO", "EN MI CANAL · SEGUIME"]
}
```

| Clave | Qué es | Rango útil |
|---|---|---|
| `ACENTO` | color de callouts, outro y CTA. **Hex de 6 dígitos** (se le concatena alpha) | claro y saturado |
| `SUB_TAMANO` / `SUB_TAMANO_SHORT` | px del subtítulo en el largo (1920×1080) y en el short (1080×1920) | 44-60 / 64-84 |
| `CRT_OP` | scanlines de tele vieja | `0` = nada, `0.5` = demo |
| `VIG_OP` | viñeta (bordes oscuros) | `0` = nada, `0.6` = demo |
| `GLITCH` | sacudón + separación RGB en cada corte | `0` = sin glitch, `1.0` = demo |
| `GLITCH_A` / `GLITCH_B` | los dos tintes del glitch | rgba |
| `OUTRO` / `CTA` | 2 líneas cada uno. `"OUTRO": []` = video sin cierre | — |

**Para un look NO retro** (divulgación, negocios, historia): `CRT_OP: 0`, `GLITCH: 0`,
`VIG_OP: 0.35`, fuente editorial. Quedan solo las imágenes con Ken Burns y los subtítulos.

## 4. Verificar antes de dar por hecho

Después de escribir el archivo, chequeá estas dos cosas — son las que rompen en silencio:

```bash
uv run python3 -c "import json;b=json.load(open('$HOME/.faceless/brand.json'));\
a=b.get('ACENTO','#7dffb4');\
assert a.startswith('#') and len(a)==7, f'ACENTO debe ser hex #rrggbb, vino {a}';\
r,g,bl=(int(a[i:i+2],16) for i in (1,3,5));\
lum=(0.299*r+0.587*g+0.114*bl)/255;\
print('OK. Luminancia sobre negro:',round(lum,2), '(bajo 0.35 se lee mal en pantalla)')"
```

Y confirmá que las fuentes que elegiste están en la tabla del paso 2, o que el usuario las tiene
instaladas de verdad.

## 5. Usarla

A partir de acá, **todos** los comandos de armado llevan la marca primero:

```bash
uv run python3 "${CLAUDE_PLUGIN_ROOT}/scripts/armar_video_hf.py" <proyecto> <transcript.json> <voz.wav> \
  --config ~/.faceless/brand.json --config <proyecto>/config.json
```

El orden importa: primero la marca (permanente), después el caso (puede pisar la marca si ese
video puntual necesita otra cosa).

**Dónde se ve el resultado:** en el paso 7 del skill `nuevo-documental`, con
`npx hyperframes snapshot --at 5,30,60`. Ahí mirás el contact-sheet antes de renderizar los
minutos completos — si el color o el subtítulo no te gustan, tocás el `brand.json` y volvés a
armar el HTML (son 2 segundos, no hay que re-renderizar nada).
