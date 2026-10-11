<h1 align="center">NarraReel</h1>

<p align="center"><strong>Your script. Your voice. Viral captions. 100% open source.</strong></p>

<p align="center">
  <a href="https://github.com/SanTiwari07/NarraReel/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/SanTiwari07/NarraReel/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Licence: MIT" src="https://img.shields.io/badge/licence-MIT-faff69?labelColor=0a0a0a">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-faff69?labelColor=0a0a0a">
  <a href="notebooks/NarraReel_Colab.ipynb"><img alt="Open in Colab" src="https://colab.research.google.com/assets/colab-badge.svg"></a>
</p>

<p align="center"><img src="docs/assets/demo.gif" alt="A NarraReel video: each word is highlighted as it is spoken" width="270"></p>

NarraReel turns **the script you wrote** into a Reel, Short or YouTube video: narrated in a free AI voice
(online or fully offline) or **your own cloned voice**, timed to the **exact length you ask for**, with
**word-synced captions** in styles made for short video. It runs on your computer. No account, no API key, no
watermark from us.

The clip above was made with NarraReel itself, from [this script](docs/assets/demo-script.txt).

## Why NarraReel

- **Your voice, with energy.** Record 30 seconds and narrate in your own voice, then dial the delivery from
  calm to hype. AI voices that sound flat are the reason most faceless videos get skipped.
- **Exact length.** "Make this 60 seconds" lands on the second: NarraReel stretches the pauses between
  sentences first (it sounds natural), changes speed only for what is left, and tells you honestly how many words to add or cut.
- **Captions that keep people watching.** Every word is highlighted at the moment it is spoken, using the voice
  engine's own word timings. Eight presets, 18 bundled fonts, a live preview, and a transparent overlay export
  for your editor.
- **Open and local.** MIT code, commercial-friendly models, fonts you may ship. Works offline after one model download.

## Quick start

You need Python 3.10+ and [ffmpeg](https://ffmpeg.org/) with libass (`winget install Gyan.FFmpeg`,
`brew install ffmpeg`, or `sudo apt install ffmpeg`).

```bash
git clone https://github.com/SanTiwari07/NarraReel.git
cd NarraReel
pip install -e ".[server]"
narrareel doctor                  # checks ffmpeg, voices and disk space
narrareel serve --open            # the web app: script, duration, voice, captions, export
```

The repository ships the web app's source; to build it, run `npm ci && npm run build:wheel` in `frontend/` once
(Node 22). Released packages will include it already.

Optional extras: `".[offline]"` offline voices (Kokoro), `".[align]"` precise word timing for any voice,
`".[clone]"` your own cloned voice ([details](docs/voice-cloning.md)).

With Docker:

```bash
docker build -f docker/Dockerfile -t narrareel .
docker run -p 8765:8765 -v narrareel-data:/data narrareel     # open the link it prints
```

## The five steps

1. **Script**: paste or drop a `.txt`/`.md`. Live word count, estimated length, warnings for numbers, URLs and very long sentences.
2. **Duration**: pick a target (15 s to 10 min, or type `6m`). See three honest options: edit the script (with the
   exact number of words to add), adjust pauses and delivery, or change the speed. Each is badged *natural*,
   *noticeable*, *strong* or *not recommended*.
3. **Voice**: online and offline voices with samples, or your own cloned voice. Speed and energy, and a quick preview.
4. **Captions**: format (Reels, YouTube, square, 4:5), style, font, colours, position, background (colour, image,
   video loop or transparent). The preview frame is rendered by the same renderer as the final video.
5. **Export**: MP4, or WebM / ProRes with transparency. You also get the voiceover (MP3, WAV), subtitles (SRT, styled ASS),
   per-word timings (JSON) and a project file. Restyling later reuses the voiceover.

<p align="center"><img src="docs/assets/presets.png" alt="The eight caption presets" width="560"></p>

### Caption styles

| Style (`--style <id>`) | Look |
|---|---|
| `minimal` | Small white text, no highlight |
| `boxed` | White text, word highlight |
| `karaoke` | Green karaoke word highlight |
| `neon` | Pale text, yellow word highlight |
| `bold-pop` | Large black type, yellow highlight |
| `one-word` | One huge word at a time |
| `keyword-emphasis` | Key words emphasised in yellow |
| `subtitle-classic` | Classic centred subtitles |
| `typewriter` | Ink on paper, red ribbon highlight |
| `highlighter` | Marker-pen yellow box sweeping behind the active word |

List them any time with `narrareel styles`.

## Command line

```bash
narrareel voices --lang en                              # <engine>:<voice> references
narrareel analyze script.txt --target 6m                # how long is it, and how do I fit 6:00?
narrareel speak script.txt --target 60s                 # narration, word timings, subtitles
narrareel make script.txt --target 60s --style boxed -o reel.mp4
narrareel make script.txt --background transparent --style neon -o captions.webm
narrareel preview script.txt --style karaoke -o frame.png
narrareel clone me.wav --name "My voice" --i-have-consent
narrareel make script.txt --voice chatterbox:my-voice --energy 0.8 -o reel.mp4
```

Every command has `--help`; most take `--json`.

## How it compares

| | NarraReel | AI-video generators (e.g. MoneyPrinterTurbo, ShortGPT) | Voice studios (e.g. VoiceStudio) |
|---|---|---|---|
| You write the script | **Yes**, that is the point | They write it from a topic | n/a |
| Exact duration targeting | **Yes** | No | No |
| Your cloned voice, energy control | **Yes** | Mostly stock voices | Yes |
| Word-synced animated captions | **Yes**, presets + fonts + preview | Basic subtitles | No |
| Stock footage / B-roll | Your own background only | **Yes** | No |
| Licence | MIT | MIT | AGPL-3.0 |

Based on each project's own description when we compared them (October 2026); corrections are welcome. Different
tools for different jobs: if you want a video generated from a topic, those projects are further along than we are.

## Responsible use

Clone only your own voice, or a voice you have explicit permission to use. NarraReel asks every time and records
the confirmation, keeps the model's inaudible watermark on, and has no "clone from a link" feature. Read
[docs/voice-cloning.md](docs/voice-cloning.md). Many platforms require labelling AI-generated content; check the
current rules of the platform you post on.

## Status and roadmap

Working today: script analysis, exact-length narration, Edge (online) and Kokoro (offline) voices, word timing
(native, estimated, or aligned with Whisper), 8 caption presets, 5 formats, transparent export, the web app, the
CLI, and the voice-cloning flow and engine. The cloning engine is verified with a stand-in model in tests; run the
check in [docs/voice-cloning.md](docs/voice-cloning.md) with your own recording and tell us how it sounds.

Next: PyPI release, demo Space, more languages (Hindi voices and fonts work today; first-class Hinglish tooling is
planned), background music with ducking. The plan and decisions live in [WHAT_TO_DO.md](WHAT_TO_DO.md).

## Contributing

Presets, fonts, formats and engines are plain files and small classes: see [CONTRIBUTING.md](CONTRIBUTING.md).
Good first issues are listed there.

## Credits and licence

NarraReel is [MIT](LICENSE). It stands on [edge-tts](https://github.com/rany2/edge-tts),
[Kokoro](https://github.com/hexgrad/kokoro) via [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx),
[Chatterbox](https://github.com/resemble-ai/chatterbox),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper), [ffmpeg](https://ffmpeg.org/) and libass, and the
[Google Fonts](https://fonts.google.com/) families we bundle. Every dependency, model and font with its licence is
in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). NarraReel started life as "Text2Reel Generator".
