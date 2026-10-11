# Third-party licences

NarraReel's own code is MIT (see `LICENSE`). This file lists everything else it depends on or
downloads. Rules are in `WHAT_TO_DO.md` section 6.2. Versions are those checked on 2026-10-10.

## Core install (`pip install narrareel`)

Verified by `scripts/check_licenses.py` in CI: every package must be MIT, BSD, Apache-2.0, ISC,
PSF, MPL-2.0, HPND/MIT-CMU or LGPL.

| Component | Version | Licence | Use |
|---|---|---|---|
| edge-tts | 7.2.x | LGPL-3.0 | Online Microsoft Edge voices (unmodified library, installed from PyPI) |
| numpy | 2.x | BSD-3-Clause | Audio assembly |
| fonttools | 4.x | MIT | Reading font names and glyph coverage |
| Pillow | 11-12 | MIT-CMU (HPND) | Font previews, text measuring |
| pydantic | 2.x | MIT | Shared data models |
| Typer (+ Rich, Click) | 0.2x | MIT / BSD | Command line |
| aiohttp and friends | - | Apache-2.0 / MIT / PSF | Dependencies of edge-tts |

## Optional extras

| Extra | Component | Licence | Plain-English note |
|---|---|---|---|
| `[offline]` | kokoro-onnx 0.6.x | MIT | Runs the Kokoro model with ONNX Runtime |
| `[offline]` | onnxruntime | MIT | Model runtime |
| `[offline]` | **phonemizer / phonemizer-fork** | **GPL-3.0+** | Text to phonemes. Installed from PyPI by the user, never copied into this repo |
| `[offline]` | **espeak-ng** (via espeakng-loader) | **GPL-3.0** | Phoneme engine used by phonemizer |
| `[align]` | faster-whisper | MIT | Precise word timing (forced alignment) |
| `[align]` | CTranslate2, tokenizers, PyAV | MIT / Apache-2.0 / BSD | Dependencies of faster-whisper |
| `[clone]` | chatterbox-tts | MIT | Voice cloning with energy control |
| `[clone]` | PyTorch, torchaudio | BSD-3-Clause | ML runtime |
| `[server]` | FastAPI, Starlette | MIT / BSD-3-Clause | Web API |
| `[server]` | uvicorn, sse-starlette, python-multipart | BSD-3-Clause / BSD-3-Clause / Apache-2.0 | Web server pieces |

**Why GPL inside an optional extra is fine:** GPL is an open-source licence. The concern is
distributing a *combined* work. NarraReel never copies GPL code into its repository; users who
choose `pip install "narrareel[offline]"` install those packages themselves. The core install
stays free of GPL components. If you ship a Docker image that includes `[offline]`, include the
GPL licence texts and a pointer to the espeak-ng and phonemizer sources.

## Models (downloaded on first use, never committed)

| Model | Licence | Source |
|---|---|---|
| Kokoro-82M weights (ONNX export) | Apache-2.0 | https://huggingface.co/hexgrad/Kokoro-82M , ONNX files from https://github.com/thewh1teagle/kokoro-onnx/releases |
| Whisper `base` (via faster-whisper, CTranslate2 conversion) | MIT | https://huggingface.co/Systran/faster-whisper-base |
| Chatterbox weights (Phase 4) | MIT | https://huggingface.co/ResembleAI/chatterbox |

Chatterbox output carries Resemble AI's Perth watermark. NarraReel keeps it enabled.

## External programs

| Program | Licence | Use |
|---|---|---|
| ffmpeg (with libass) | LGPL-2.1+ or GPL-2+ depending on the build | Called as a separate program: decoding, effects, rendering |

## Fonts (Phase 2)

Only OFL-1.1 or Apache-2.0 fonts are bundled, each next to its licence file under
`narrareel/assets/fonts/`. See `narrareel/assets/fonts/manifest.json` for the full list.

| Family | Licence | Source |
|---|---|---|
| Montserrat | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Montserrat) |
| Anton | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Anton) |
| Bebas Neue | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Bebas+Neue) |
| Poppins | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Poppins) |
| Oswald | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Oswald) |
| Archivo Black | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Archivo+Black) |
| Bangers | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Bangers) |
| Luckiest Guy | Apache-2.0 | [Google Fonts](https://fonts.google.com/specimen/Luckiest+Guy) |
| Lilita One | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Lilita+One) |
| Permanent Marker | Apache-2.0 | [Google Fonts](https://fonts.google.com/specimen/Permanent+Marker) |
| Caveat Brush | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Caveat+Brush) |
| Inter | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Inter) |
| Rubik | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Rubik) |
| Kanit | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Kanit) |
| Roboto Condensed | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Roboto+Condensed) |
| Noto Sans Devanagari | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Noto+Sans+Devanagari) |

## Not used (and why)

F5-TTS weights (CC-BY-NC), XTTS-v2 (Coqui Public Model License), Fish Speech and Spark-TTS
weights (CC-BY-NC-SA) are non-commercial and excluded. VoiceStudio (AGPL-3.0) is never imported;
it may only be reached as a separate service.
