# faceless-agent

Turn a **script and your recorded voice** into a cinematic **faceless documentary** — AI-generated
images, Ken Burns motion, glitch transitions, a CRT look, synced subtitles, music and SFX — plus a
matching **vertical short**. A Claude Code plugin.

The human parts stay human (script + voice); AI only handles production. That keeps it on the right
side of YouTube's authenticity rules — add an AI-production disclosure in your description.

## Install

```
/plugin install faceless-agent --marketplace MartinOlivero/faceless-agent
```

On Claude Code older than 2.1.275, use the two-step form:

```
/plugin marketplace add MartinOlivero/faceless-agent
/plugin install faceless-agent
```

## Status

Early release. The full pipeline — long form and vertical short — has been run end to end **on
macOS only**. CI runs the config tests and the dependency check on Linux and Windows too, which is
not the same as rendering a video there. `setup` carries
install commands for Linux and Windows, but those paths are untested — issues welcome.

The skills are written in **Spanish** (Claude will still answer in your language). Transcription
defaults to Spanish; pass a language code for anything else (see `nuevo-documental`, step 3).

## Use

1. **Set up once** — run the `setup` skill ("configurá el plugin"). It detects your OS, offers to
   install the free tools (ffmpeg, Node ≥22, uv), and guides the paid API keys with their real cost.
2. **Make it yours** — run the `brand-setup` skill ("configurá mi marca"). It interviews you and
   writes `~/.faceless/brand.json`: accent color, fonts, subtitle size, how much CRT/glitch/vignette
   you want (zero is a valid answer), outro and short CTA. **Skip this and your videos will look
   like someone else's channel** — the plugin ships with the demo brand.
3. **Make a documentary** — run the `nuevo-documental` skill ("armemos un caso"). It walks the full
   pipeline: script → master voice → transcribe → AI images → assemble motion+effects → render →
   mix audio → build the vertical short → cover image.

## What's inside

- `scripts/doctor.py` — dependency check (JSON), used by `setup`.
- `scripts/config_comun.py` — the config vocabulary shared by all three engines. A key that isn't
  in it is a typo, and the run stops instead of silently falling back to the demo values.
- `scripts/transcribir.py` — voice → `transcript.json` (word-level timings, faster-whisper).
- `scripts/armar_video_hf.py` — builds the HyperFrames HTML (Ken Burns, glitch, subtitles).
- `scripts/mezclar_audio.py` — mixes voice + music + SFX over the silent render (ffmpeg).
- `scripts/armar_short_hf.py` — builds the 9:16 short from the hook.

Each assembly script ships with demo values (the Stuxnet pilot) and takes `--config file.json`,
which can be repeated and is applied in order. The standard call is
`--config ~/.faceless/brand.json --config <project>/config.json`: the channel's look first
(permanent, written by `brand-setup`), then this video's timing (written by `nuevo-documental`).

## Dependencies

**Free (system):** ffmpeg, Node ≥22, uv, [HyperFrames](https://hyperframes.dev) (video engine, via
`npx`). **Paid (per-use APIs):** Gemini (images), optionally kie.ai (hero video). **Music/SFX:**
HeyGen via HyperFrames (`npx hyperframes auth login`). The `setup` skill explains each with cost.

## License

MIT © Martín Olivero / IamAutom
