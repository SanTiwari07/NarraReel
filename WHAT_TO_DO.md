# NarraReel — WHAT_TO_DO.md (Master Plan)

> **Your script. Your voice. Viral captions. 100% open source.**

| | |
|---|---|
| Project name | **NarraReel** (was "Text2Reel Generator") |
| Repo | `github.com/SanTiwari07/Text2ReelGenerator` → to be renamed `SanTiwari07/NarraReel` |
| Python package | `narrareel` (`pip install narrareel`, command `narrareel`) — name verified free on PyPI and GitHub on 2026-10-10 |
| Licence | MIT |
| Document created | 2026-10-10 |
| Current phase | **Phases 1–4 implemented and checked, Phase 5 prepared (only owner actions remain)** (see section 16 for what is verified and what is left for the owner) |

---

## 0. How to use this document

This file is the single source of truth for **what NarraReel is, why it exists, how it is built, and what to do next**. It is written so that:

- the owner (SanTiwari07) can check every decision in one place,
- any contributor can pick up a task without asking questions,
- any AI coding session (or similar tool) can read this file first and have full context.

**Rules for keeping it useful**

1. When a decision changes, update this file in the same commit as the code change.
2. When a task is done, tick its checkbox and add the commit hash if useful.
3. Anything marked **⚠️ VERIFY** is a fact that was not confirmed at writing time. Confirm it before relying on it, then remove the marker.
4. Section 13 (Decision log) records *why* we chose things. Add to it; don't rewrite history.

**Status legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `⏸` postponed · `⚠️ VERIFY` unconfirmed fact

---

## Table of contents

1. Vision and goals
2. Current state audit (what exists today)
3. The product: user flow, step by step
4. Architecture
5. Feature specifications (in depth)
6. Tech stack, licences, and open-source rules
7. Phases and tasks (Phase 1 in full detail)
8. Testing strategy
9. Packaging, install, Docker, Colab, Hugging Face Space
10. Documentation and community
11. Launch and star-growth plan
12. Risks and mitigations
13. Decision log and open questions
14. Glossary
15. Appendix: references, command cookbook, sample files

---

## 1. Vision and goals

### 1.1 The origin story (why this exists)

The owner was making demo videos and Reels and did not want to record their own voice every time, so they used AI text-to-speech. Two problems appeared:

1. **The AI voice had less energy than their real voice.** It sounded flat, didn't feel real, and viewers skipped it.
2. **Captions matter.** Word-by-word animated captions are a big part of why Reels and Shorts feel addictive and keep people watching. Getting them right by hand is slow.

NarraReel solves both: a creator pastes their own script, picks how long the video should be, picks a voice (a free AI voice **or their own cloned voice with adjustable energy**), picks a caption look, and gets a finished video with perfectly-synced, good-looking captions.

### 1.2 One-line pitch

> NarraReel turns your script into a Reel, Short, or YouTube video — narrated in a free AI voice or **your own cloned voice**, timed to the exact length you want, with viral-style animated captions. Runs locally. 100% open source.

### 1.3 Goals

| ID | Goal | How we'll know |
|---|---|---|
| G1 | **100% open source.** Every line of our code is MIT. Every default dependency, model and font is under an open licence that allows commercial use. | Licence CI check passes; `THIRD_PARTY_LICENSES.md` complete |
| G2 | **100–200+ GitHub stars.** | Star count; this drives everything in Sections 10–11 |
| G3 | **Usable by everyone.** No account, no API key, no payment, no GPU required for the basic flow. Works on Windows, macOS, Linux. | Fresh-machine install test on all three OSes passes; CPU-only path works |
| G4 | **Quality that competes with paid tools.** Captions in perfect sync; voices that don't sound flat; renders fast. | Caption drift < 80 ms; 60-second Reel renders in < 30 s on a normal laptop (target) |
| G5 | **Easy to contribute to.** New fonts, caption styles, voices and formats can be added without touching core logic. | Presets are JSON files; engines are plugins; good-first-issues exist |

### 1.4 Non-goals (things we deliberately don't do, at least for now)

- **AI writing the script for you.** The user brings their own script. (An *optional* "help me trim/expand" rewrite is on the backlog, never required.) This is the main difference from MoneyPrinterTurbo.
- **Stock footage / B-roll generation.** Backlog item, not core.
- **A hosted SaaS.** NarraReel runs on the user's machine. A free Hugging Face Space demo is fine, but we don't run a paid service.
- **Cloning someone else's voice without permission.** Consent is required in the flow (Section 5.8).
- **Mobile apps.** Desktop/browser only.

### 1.5 Who it's for (personas)

1. **The faceless creator** — runs a Reels/Shorts channel, writes scripts, doesn't want to record voice every day. Wants volume and speed.
2. **The founder/dev making demo videos** (the owner's own case) — needs a clean voiceover + captions for product demos, doesn't want to use their own voice, but wants it to sound energetic and real.
3. **The educator** — makes 5–10 minute YouTube explainers, cares about exact duration and readable captions.
4. **The editor** — already uses CapCut/Premiere/DaVinci; wants just the voiceover + a transparent caption overlay or an `.srt` to drop into their timeline.
5. **The non-English creator** — e.g. Hindi/Hinglish content. Needs fonts that render Devanagari and voices in their language. (Partial support in Phase 1–2, improved later.)

### 1.6 Competition and positioning

Checked on GitHub on 2026-10-10:

| Project | Stars | Licence | What it does | How we differ |
|---|---|---|---|---|
| harry0703/MoneyPrinterTurbo | ~129k | MIT | AI writes script from a topic, adds stock footage, TTS, subtitles | They automate *content*. We serve creators who write their own script and want **their own voice** + duration control + premium captions |
| RayVentura/ShortGPT | ~8k | MIT | Automated short video framework | Same as above — automation-first |
| debpalash/VoiceStudio | ~56.7k | **AGPL-3.0** | Local voice cloning / dubbing studio (ElevenLabs alternative) | They are a voice studio. We are a *script → finished video* tool. We may connect to VoiceStudio optionally, never copy its code |
| unconv/captacity | ~139 | MIT | Adds captions to videos | Captions only, no voice |
| ColinGPT9/clips-studio | ~93 | AGPL-3.0 | AI video clipper (Opus Clip alternative) | Cuts existing long videos; we create from a script |

**Our unique combination (nobody else has all three):**

1. **Duration targeting** — "make this script exactly 6:00", with honest advice (edit the script vs change the speed).
2. **Your own voice with energy control** — clone from a 30-second recording, then dial energy Calm → Hype.
3. **Reels-grade captions** — many fonts, animated presets, live preview, transparent overlay export.

### 1.7 Success metrics

- Stars: 100 within ~1 month of launch, 200+ after the second launch wave.
- Time-to-first-video for a new user: under 5 minutes from `git clone` (or under 2 minutes with Docker).
- Issues opened by people other than the owner (a sign of real usage).
- At least 3 external contributors (fonts, presets, translations are the easy entry points).

---

## 2. Current state audit (what exists today)

Audit done on 2026-10-10 against commit `e1a210f` plus uncommitted changes.

### 2.1 Files

| File | Lines | What it does | Fate |
|---|---|---|---|
| `app.py` | 243 | Streamlit UI: script box, voice picker, speed, colours, fonts, size, words-per-chunk, position, generate + download | Move to `legacy/` in Phase 1; delete when React UI ships (Phase 3) |
| `generator.py` | 284 | `ReelGenerator`: 15 Edge-TTS voices, Pillow text rendering with word highlight, MoviePy compositing, MP4/WebM export | Logic is rewritten into `narrareel/` modules; file moves to `legacy/` |
| `utils.py` | 21 | `hex_to_rgb`, `estimate_duration` (150 wpm), `split_text_into_chunks` (unused) | Replaced by `narrareel/script/` and `narrareel/captions/` |
| `requirements.txt` | 5 | streamlit, moviepy, edge-tts, pillow, numpy | Replaced by `pyproject.toml` |
| `README.md` | — | Feature list, install, usage | Rewritten in Phase 5; minimal update in Phase 1 |
| `test_gen.py`, `test_tts_timing.py` | — | Deleted in the working tree (not committed) | Commit the deletion; real tests go in `tests/` |
| `temp/`, `__pycache__/` | — | Untracked generated files | Ignored via `.gitignore` |

Uncommitted change in `generator.py`: adds `os.makedirs(TEMP_DIR, exist_ok=True)` before writing `voice.mp3`.

### 2.2 How the current pipeline works

1. Edge-TTS generates `temp/voice.mp3` with `rate="+N%"` from the speed slider.
2. The audio duration is read with MoviePy.
3. **Timing is guessed**: total duration ÷ total characters = seconds per character; each word gets `len(word) × that`. Pauses, punctuation and speaking rhythm are ignored, so captions drift.
4. Words are grouped into chunks of `max_words`.
5. For **every word**, Pillow draws a full 1080×1920 RGBA image of the chunk with that word highlighted, wrapped in a MoviePy `ImageClip`.
6. MoviePy composites hundreds of full-frame clips over a `ColorClip` and encodes at 24 fps (`libx264 ultrafast` or `libvpx-vp9` with alpha).

### 2.3 Problems found

**Repo / project**
- No `LICENSE` file (README links to one that doesn't exist).
- No `.gitignore`; `__pycache__/`, `temp/` sit untracked; risk of committing generated media.
- No tests, no CI, no CLI, no Docker, no packaging.
- Sidebar image is hot-linked from flaticon.com — external licensing terms and a network dependency. Must be replaced with our own asset.

**Architecture**
- One class does everything; UI calls internal methods (`generate_audio`) directly.
- Fixed output paths (`temp/voice.mp3`, `temp/output_reel.mp4`): two runs overwrite each other; previews overwrite the main audio.
- `asyncio.run()` called inside Streamlit callbacks — works, but fragile.

**Duration**
- Estimate is a fixed 150 wpm; ignores voice, speed, and pauses.
- No target duration, no required-speed calculation, no warnings, no edit suggestions.
- Speed limited to 0.5–1.5×.

**Voice**
- Only Edge-TTS — an online Microsoft service accessed unofficially. It can break or rate-limit at any time.
- No offline voice, no energy control, no cloning, no saved voices.

**Caption timing**
- Character-proportional guess → visible drift, worse on long scripts.

**Captions / fonts**
- 8 fonts mapped to **Windows** system files (`arial.ttf`, `impact.ttf` …). On macOS/Linux these fail and fall back to DejaVu or Pillow's tiny default font — every font looks the same.
- One visual style. No animations, no presets, no preview, no custom font upload.
- Text wrapping uses a fixed 100 px margin; line height is `fontsize + 10`.
- Only vertical 1080×1920. No YouTube/Instagram formats, no `.srt` export.

**Rendering**
- One full-frame image per word, composited by MoviePy → very slow and memory-hungry for 5–10 minute videos.

**UI**
- Single page instead of a guided flow; dark theme hard-coded in CSS; emoji-heavy labels.

### 2.4 Environment facts (owner's machine, checked 2026-10-10)

- Windows 11, venv on **Python 3.13.6**.
- Installed: edge-tts 7.2.7, moviepy 2.2.1, streamlit 1.52.2, pillow 11.3.0, numpy 2.4.0, imageio-ffmpeg 0.6.0.
- System ffmpeg: **8.0.1 (gyan.dev essentials build)** at `C:\ProgramData\chocolatey\bin\ffmpeg` — **includes libass** (`ass` and `subtitles` filters present). ✅ Our planned renderer works on this machine.
- `kokoro` (official, PyTorch) requires Python `<3.13` → **cannot install in this venv**. `kokoro-onnx` 0.6.1 supports `>=3.10,<3.14` → OK.
- `chatterbox-tts` 0.1.7 pins `torch==2.6.0` for Python <3.14. Verified 2026-10-10: torch 2.6.0 (CPU) installs on Windows + Python 3.13.

---

## 3. The product: user flow, step by step

NarraReel is a **5-step wizard**. Each step has one job. The user can go back to any earlier step; later steps update automatically.

```
1. Script ─► 2. Duration ─► 3. Voice ─► 4. Captions ─► 5. Export
                 │
                 ├─ Option A: edit the script (add/cut N words)
                 └─ Option B: change speed / pauses
```

A persistent **summary bar** (top or side) always shows: word count · estimated length · target length · chosen voice · format.

### 3.1 Step 1 — Script

**User does:** pastes or types the script. Can also drop a `.txt`/`.md` file.

**App shows instantly (client-side, no server round trip for basic counts; server for accurate estimate):**

> 742 words · 38 sentences · 6 paragraphs · **≈ 4:57 at 1.0×** (with "Jenny (US)" voice)

**Details**
- Live counts update as the user types (debounced ~300 ms for the server estimate).
- Sentence list view (collapsible): each sentence with its own estimated seconds — helps users see which sentences are long.
- Warnings:
  - Very long sentence (> 35 words): "Long sentences sound rushed and make captions harder to read. Consider splitting."
  - Numbers, symbols, URLs, emoji: "These may be read oddly. Preview to check." (e.g. "2026", "$5k", "→")
  - Empty script: Next button shows inline error.
  - Very long script (> 3,000 words ≈ 20 min): allowed, but warn about generation time.
- Language auto-detect hint (Latin vs Devanagari script) → pre-filters voices in Step 3.

**Output of this step:** `ScriptAnalysis` (Section 4.4).

### 3.2 Step 2 — Duration

**User does:** picks a target length — quick buttons (15 s, 30 s, 60 s, 90 s, 3 min, 5 min, 10 min), a custom field ("6m", "6:00", "90s", "1m30s"), or "No target, just use speed" with speed buttons (0.75×, 1×, 1.25×, 1.5×, 2×).

**App shows (example: script ≈ 4:57, target 6:00):**

> Your script is about **1:03 shorter** than your target.
>
> **Option A — Edit the script** (best quality)
> Add about **155 words** to reach 6:00 at natural speed. *[Edit script]* — opens the editor with a live timer.
>
> **Option B — Adjust delivery** (no script changes)
> Speed **0.92×** + slightly longer pauses between sentences. 🟢 Sounds natural.
> *[Use this]*

The speed quality badge:

| Speed range | Badge | Message |
|---|---|---|
| 0.90 – 1.15× | 🟢 Natural | "Sounds natural." |
| 0.80 – 0.90× or 1.15 – 1.30× | 🟡 Noticeable | "Listeners may notice, but it's fine." |
| 0.70 – 0.80× or 1.30 – 1.50× | 🟠 Strong | "Sounds noticeably slow/fast. Editing the script is better." |
| < 0.70× or > 1.50× | 🔴 Not recommended | "This will sound unnatural. Edit the script instead." |

Manual speed is still allowed from 0.5× to 2.0× — we warn, we don't block.

**How Option B stretches time:** for a *longer* target we add pause time between sentences first (pauses sound natural; slowed speech sounds dragged), then slow the voice only as much as still needed. For a *shorter* target we shorten pauses first, then speed up. Exact algorithm in Section 5.2.

**Output:** `DurationPlan` (Section 4.4).

### 3.3 Step 3 — Voice

Two tabs:

**Tab "AI voices"**
- Grouped by engine:
  - **Offline voices (Kokoro)** — runs on your computer, no internet after a one-time model download. Badge: "Offline".
  - **Online voices (Microsoft Edge)** — high quality, needs internet, unofficial service. Badge: "Online".
- Filters: language, accent (US/UK/IN/…), gender, engine.
- Each voice card: name, accent, gender, ▶ 5-second sample (cached), "Use".

**Tab "My voice"** (Phase 4)
- List of saved cloned voices (name, created date, ▶ sample, delete).
- "+ Clone my voice": record in browser (or upload) → guided paragraph to read → quality check → consent checkbox → saved. (Section 5.8.)
- If the cloning engine isn't installed: a friendly card explaining how to install it (`pip install "narrareel[clone]"`) or use the free Colab notebook.

**Controls under the tabs**
- **Speed** — prefilled from Step 2 (changing it updates the Step 2 plan).
- **Energy** — Calm / Normal / Hype (+ fine slider). For cloned voices this maps to Chatterbox's `exaggeration`/`cfg_weight`; for AI voices it maps to small pitch/rate/volume changes plus audio processing (Section 5.4). The UI is honest: "Energy works best with your own voice."
- **Preview** — synthesizes only the first 1–2 sentences with current settings (a few seconds) and plays it.

**Output:** `VoiceSelection` = engine + voice id + speed + energy.

### 3.4 Step 4 — Captions

Order inside the step: **Format → Font → Style preset → Fine-tune**, with a **live preview** panel.

1. **Format** (sets resolution + safe zones + default caption position):
   - Reels / TikTok / Shorts — 9:16, 1080×1920
   - YouTube — 16:9, 1920×1080
   - Instagram post — 1:1, 1080×1080
   - Instagram portrait — 4:5, 1080×1350
   - Audio only (no video; skips caption styling except `.srt`)
2. **Font** — a visual grid: each card shows sample caption text ("THIS IS YOUR CAPTION") rendered *in that font*. ~15 bundled fonts + "Upload your font (.ttf/.otf)". Filter by vibe: Bold / Clean / Fun / Handwritten / Multilingual.
3. **Style preset** — cards with an animated thumbnail: Bold Pop, Karaoke Highlight, Boxed, Minimal, One Word, Neon, Keyword Emphasis, Subtitle Classic.
4. **Fine-tune** (collapsible "Advanced"):
   - Text colour, highlight colour, outline colour/width, shadow, box colour/opacity
   - Font size, uppercase on/off
   - Words per caption (1–8), max lines (1–2)
   - Position: top / middle / lower-middle / bottom, plus a vertical offset slider
   - Animation: none / pop / bounce / fade
   - Background: solid colour / transparent (overlay) / image / video loop (image/video in Phase 2+)
5. **Live preview** — a phone-shaped (or 16:9) frame showing one rendered frame of a real caption from the user's script. Implemented as a server-rendered PNG of a single frame (Section 5.11) so it matches the final video exactly.

"Save as my preset" stores the whole caption config as JSON for next time.

**Output:** `CaptionConfig` + `FormatPreset`.

### 3.5 Step 5 — Export

- Summary of all choices.
- **Generate** → progress view with stages: Preparing → Generating voice (sentence 12/38) → Timing words → Building captions → Rendering video (43%) → Done. Cancel button.
- Results:
  - ▶ Video player
  - Downloads: video (`.mp4`, or `.webm`/`.mov` with transparency), voiceover (`.mp3` and `.wav`), subtitles (`.srt`, `.ass`), word timings (`.json`), project file (`.narrareel.json` — reopen and tweak later).
  - "Change captions and re-render" — reuses the generated voice (no re-synthesis), so tweaking style is fast.
- "Save settings as preset" → next time: paste script → one click.

---

## 4. Architecture

### 4.1 Big picture

```
┌──────────────────────────┐        HTTP/JSON + SSE        ┌──────────────────────────────┐
│  frontend/ (React + TS)  │  ───────────────────────────► │  narrareel/server (FastAPI)  │
│  5-step wizard, previews │  ◄─────────────────────────── │  routes, job queue, static   │
└──────────────────────────┘                               └──────────────┬───────────────┘
                                                                          │ calls
                                    ┌─────────────────────────────────────▼─────────────────────────────────────┐
                                    │                         narrareel core (pure Python)                       │
                                    │  script/     engines/        timing/       audio/      captions/  render/  │
                                    │  analyze     edge, kokoro,   native,       ffmpeg,     chunk,     ffmpeg   │
                                    │  duration    chatterbox…     estimate,     process     ass, srt,  render   │
                                    │                              align                     fonts               │
                                    │  pipeline/  (orchestrates)   jobs/ (workspaces)   models.py   config.py    │
                                    └────────────────────────────────────────────────────────────────────────────┘
                                                                          ▲
                              narrareel/cli.py (Typer)  ──────────────────┘   (same core, no server needed)
```

**Key rule:** the core never imports the server, the CLI, or the frontend. The server and CLI are thin layers. This lets us swap the UI (Streamlit → React → maybe desktop later) without touching the logic.

### 4.2 Repository layout (target)

```
NarraReel/
├── LICENSE                         # MIT
├── README.md
├── WHAT_TO_DO.md                   # this file
├── CONTRIBUTING.md                 # Phase 5
├── CODE_OF_CONDUCT.md              # Phase 5
├── THIRD_PARTY_LICENSES.md         # every dependency, model, font + licence
├── pyproject.toml
├── .gitignore
├── .editorconfig
├── .github/
│   ├── workflows/ci.yml            # tests + licence check (Phase 1)
│   ├── workflows/release.yml       # build frontend + publish (Phase 5)
│   └── ISSUE_TEMPLATE/             # Phase 5
├── narrareel/                      # the Python package
│   ├── __init__.py                 # __version__
│   ├── __main__.py                 # python -m narrareel
│   ├── cli.py                      # Typer CLI
│   ├── config.py                   # paths, env vars, settings
│   ├── models.py                   # dataclasses / pydantic models shared everywhere
│   ├── errors.py                   # NarraReelError hierarchy
│   ├── script/
│   │   ├── analyze.py              # normalise, sentences, words, counts
│   │   └── duration.py             # estimates, DurationPlan, parse "6m"
│   ├── engines/
│   │   ├── base.py                 # TTSEngine protocol, VoiceInfo, SynthResult
│   │   ├── registry.py             # discovers engines, lazy imports, availability
│   │   ├── edge.py                 # Microsoft Edge online voices
│   │   ├── kokoro.py               # offline Kokoro (kokoro-onnx), optional extra
│   │   ├── chatterbox.py           # cloning (Phase 4), optional extra
│   │   └── voicestudio.py          # optional external service (backlog)
│   ├── timing/
│   │   ├── native.py               # engine-provided word boundaries → WordTiming
│   │   ├── estimate.py             # sentence-anchored estimation (no extra deps)
│   │   └── align.py                # faster-whisper forced alignment, optional extra
│   ├── audio/
│   │   ├── ffmpeg.py               # find/run ffmpeg & ffprobe, capability checks
│   │   └── process.py              # decode, silence, concat, tempo, loudnorm, encode
│   ├── captions/                   # Phase 2
│   │   ├── chunk.py                # words → caption chunks/lines
│   │   ├── styles.py               # CaptionStyle model, preset loading
│   │   ├── fonts.py                # font registry, family names, previews
│   │   ├── ass.py                  # ASS subtitle writer (styles, animations)
│   │   └── srt.py                  # SRT writer (Phase 1 basic version)
│   ├── render/                     # Phase 2
│   │   ├── ffmpeg_render.py        # final video render
│   │   ├── preview.py              # single-frame PNG preview
│   │   └── legacy_moviepy.py       # temporary bridge in Phase 1 only
│   ├── pipeline/
│   │   ├── speak.py                # script + voice + plan → audio + word timings
│   │   └── make.py                 # full video pipeline (Phase 2)
│   ├── jobs/
│   │   ├── workspace.py            # unique per-run folders, cleanup
│   │   └── runner.py               # background queue, progress, cancel (Phase 3)
│   ├── server/                     # Phase 3
│   │   ├── app.py                  # FastAPI app factory, static files
│   │   ├── routes/                 # analyze, voices, preview, fonts, presets, jobs
│   │   └── static/                 # built React app (generated, not committed)
│   ├── assets/
│   │   ├── fonts/<Family>/         # .ttf files + OFL.txt / LICENSE (Phase 2)
│   │   ├── fonts/manifest.json
│   │   └── calibration/            # calibration paragraph(s) per language
│   └── presets/
│       ├── styles/*.json           # caption style presets (Phase 2)
│       └── formats/*.json          # format presets (Phase 2)
├── frontend/                       # Phase 3 — Vite + React + TypeScript
│   ├── package.json
│   ├── src/
│   │   ├── main.tsx, App.tsx
│   │   ├── api/                    # typed API client
│   │   ├── state/                  # project store (Zustand)
│   │   ├── steps/                  # ScriptStep, DurationStep, VoiceStep, CaptionsStep, ExportStep
│   │   ├── components/             # shared UI pieces
│   │   └── theme/tokens.css        # ALL colours/spacing/typography here (design md maps onto this)
│   └── vite.config.ts              # dev proxy to the API
├── tests/
│   ├── unit/                       # fast, no network, no models
│   ├── integration/                # ffmpeg-required, marked
│   └── fixtures/                   # sample scripts, tiny wavs
├── scripts/
│   ├── fetch_fonts.py              # downloads fonts + licences into assets (Phase 2)
│   └── check_licenses.py           # wraps pip-licenses with our allow-list
├── notebooks/
│   └── NarraReel_Colab.ipynb       # Phase 4: free-GPU cloning
├── docker/
│   └── Dockerfile                  # Phase 5
├── docs/                           # user docs, screenshots, demo GIF
└── legacy/                         # old Streamlit prototype (deleted after Phase 3)
    ├── app.py
    ├── generator.py
    └── utils.py
```

### 4.3 Layering rules

1. `narrareel/models.py`, `script/`, `timing/estimate.py`, `captions/` must be **pure Python + numpy/Pillow**. No network, no ML. These are unit-tested heavily.
2. Optional, heavy or copyleft dependencies (`kokoro-onnx`, `faster-whisper`, `chatterbox-tts`) are **imported lazily inside the engine/aligner module**, never at package import time. If missing, the registry reports `available=False` with a human reason ("Install with `pip install "narrareel[offline]"`").
3. All ffmpeg calls go through `audio/ffmpeg.py` (one place for path discovery, error capture, Windows quirks, logging).
4. Every pipeline function takes an explicit `workspace: Path` — no global `temp/` folder.
5. Long-running functions accept a `progress: Callable[[ProgressEvent], None] | None` and a `cancel: threading.Event | None`.

### 4.4 Core data models (sketch)

Pydantic v2 models (so the API can return them directly). Field names are final unless the decision log says otherwise.

```python
# narrareel/models.py  (sketch — not final code)

class Token(BaseModel):
    text: str               # as written in the script, incl. punctuation: "Hello,"
    norm: str               # normalised for matching: "hello"
    start_char: int         # span in normalised script text
    end_char: int
    sentence_idx: int

class Sentence(BaseModel):
    idx: int
    text: str
    paragraph_idx: int
    token_start: int        # index into ScriptAnalysis.tokens
    token_end: int          # exclusive
    ends_paragraph: bool

class ScriptAnalysis(BaseModel):
    text: str               # normalised script
    language_hint: str      # "en", "hi", "unknown" (script-based heuristic)
    tokens: list[Token]
    sentences: list[Sentence]
    word_count: int
    char_count: int         # letters/digits only, used for estimation
    paragraph_count: int
    warnings: list[ScriptWarning]

class VoiceInfo(BaseModel):
    engine: str             # "edge" | "kokoro" | "chatterbox" | ...
    id: str                 # engine-specific id, e.g. "en-US-JennyNeural", "af_heart"
    name: str               # display name, e.g. "Jenny"
    language: str           # BCP-47, e.g. "en-US"
    gender: Literal["female", "male", "neutral", "unknown"]
    accent: str | None      # "US", "UK", "IN", ...
    offline: bool
    custom: bool = False    # True for cloned voices
    sample_url: str | None = None

class VoiceSelection(BaseModel):
    engine: str
    voice_id: str
    speed: float = 1.0      # 0.5–2.0
    energy: float = 0.5     # 0.0 (calm) – 1.0 (hype); 0.5 = normal

class DurationEstimate(BaseModel):
    speech_seconds: float   # pure speech at the chosen speed
    pause_seconds: float    # default inter-sentence pauses
    total_seconds: float
    words_per_minute: float
    basis: Literal["calibrated", "default"]

class DurationOption(BaseModel):
    kind: Literal["edit_script", "adjust_delivery", "speed_only"]
    speed: float | None
    pause_scale: float | None       # 1.0 = default pauses
    words_delta: int | None         # +155 = add 155 words, -90 = cut 90
    resulting_seconds: float
    quality: Literal["natural", "noticeable", "strong", "not_recommended"]
    message: str

class DurationPlan(BaseModel):
    estimate_1x: DurationEstimate
    target_seconds: float | None
    options: list[DurationOption]
    recommended: int                 # index into options

class WordTiming(BaseModel):
    token_idx: int          # index into ScriptAnalysis.tokens
    text: str               # display text (with punctuation)
    start: float            # seconds in final audio
    end: float
    source: Literal["native", "aligned", "estimated"]

class SynthesisResult(BaseModel):
    audio_wav: Path
    audio_mp3: Path | None
    duration: float
    sample_rate: int
    words: list[WordTiming]
    sentence_spans: list[tuple[float, float]]   # start/end of each sentence in final audio

class ProgressEvent(BaseModel):
    stage: Literal["prepare", "voice", "timing", "captions", "render", "done", "error"]
    fraction: float          # 0.0–1.0 overall
    message: str
    detail: dict = {}
```

Caption/format/job models are defined in Phase 2/3 sections.

### 4.5 Files on disk

Default home: `~/.narrareel/` (override with env var `NARRAREEL_HOME`).

```
~/.narrareel/
├── models/
│   ├── kokoro/            # kokoro-v1.0.onnx, voices-v1.0.bin (downloaded on first use)
│   ├── whisper/           # faster-whisper model cache (if align extra used)
│   └── chatterbox/        # HF cache location for Chatterbox weights (Phase 4)
├── voices/                # cloned voice profiles (Phase 4)
│   └── <voice_id>/
│       ├── reference.wav
│       ├── sample.mp3
│       └── profile.json   # name, created_at, engine, consent record, settings
├── fonts/user/            # user-uploaded fonts
├── presets/user/          # user-saved caption presets
├── cache/
│   ├── voice_samples/     # 5-second voice previews
│   ├── calibration.json   # measured chars/sec per (engine, voice, speed)
│   └── edge_voices.json   # cached Edge voice list (refresh every 24 h)
└── jobs/
    └── 2026-10-10_153012_a1b2c3/
        ├── project.json        # full input: script, plan, voice, captions, format
        ├── sentences/0000.wav  # per-sentence audio (lets us re-time cheaply)
        ├── voice.wav           # final narration (48 kHz mono, loudness-normalised)
        ├── voice.mp3
        ├── words.json          # list[WordTiming]
        ├── captions.ass        # Phase 2
        ├── captions.srt
        ├── fonts/              # only the fonts this job needs (for libass fontsdir)
        ├── output.mp4 / output.webm / output.mov
        └── log.txt
```

Cleanup: keep the latest 20 jobs and anything newer than 7 days (configurable). `narrareel clean` removes the rest.

### 4.6 Configuration

| Env var | Default | Meaning |
|---|---|---|
| `NARRAREEL_HOME` | `~/.narrareel` | Data directory |
| `NARRAREEL_FFMPEG` | auto (PATH) | Path to ffmpeg binary |
| `NARRAREEL_FFPROBE` | auto | Path to ffprobe |
| `NARRAREEL_DEVICE` | `auto` | `cpu`, `cuda`, `mps` for ML engines |
| `NARRAREEL_HOST` / `NARRAREEL_PORT` | `127.0.0.1` / `8765` | Server bind (Phase 3) |
| `NARRAREEL_TOKEN` | unset | Required if binding to non-loopback (Phase 3) |
| `NARRAREEL_KEEP_JOBS` | `20` | Cleanup policy |
| `VOICESTUDIO_URL` | unset | Optional external VoiceStudio backend (backlog) |

Settings can also live in `~/.narrareel/config.toml`; env vars win.

### 4.7 Errors

```
NarraReelError
├── DependencyMissing     # optional extra not installed → message includes pip command
├── FFmpegError           # includes the command (redacted) and last 30 lines of stderr
├── EngineError           # engine failed (network, model, bad voice id)
│   └── EngineUnavailable
├── ScriptError           # empty script, unsupported characters
├── ModelDownloadError
└── JobCancelled
```

Every error message must say **what happened and what to do**, e.g. "Couldn't reach Microsoft's voice service. Check your internet connection, or switch to an offline voice."

### 4.8 Logging

Standard `logging`, logger names `narrareel.*`. CLI `-v` = INFO, `-vv` = DEBUG. Each job writes `log.txt` in its folder. Never log the full script at INFO (privacy); DEBUG may.

---

## 5. Feature specifications (in depth)

### 5.1 Script analysis (`narrareel/script/analyze.py`) — Phase 1

**Normalisation**
1. Unicode NFC.
2. Convert Windows line endings; strip trailing spaces per line.
3. Collapse runs of spaces/tabs to one space.
4. Two or more newlines = paragraph break. Single newline = also treated as a sentence break *if* the line doesn't end with punctuation (scripts are often written one line per thought).
5. Smart quotes/dashes are kept for display; `norm` versions are ASCII-folded and lower-cased for matching.

**Sentence splitting** (no heavy NLP dependency):
- Split after `.`, `!`, `?`, `…`, `।` (Devanagari danda), `॥`, followed by whitespace/end, and on line breaks per rule 4.
- Don't split on: common abbreviations (`Mr.`, `Mrs.`, `Ms.`, `Dr.`, `Prof.`, `St.`, `vs.`, `etc.`, `e.g.`, `i.e.`, `U.S.`, `a.m.`, `p.m.`), decimals (`3.5`), initials (`J. K.`), ellipsis inside a sentence followed by lower-case.
- Fragments without terminal punctuation that are shorter than 2 words are merged into the previous sentence. Short sentences *with* terminal punctuation ("Yes.", "Wait!") stay separate — they're deliberate beats.
- Very long sentences (> 60 words) are split for **synthesis** at `;`, `:`, `—`, or `,` nearest the middle, but kept as one sentence for display. (Long inputs make some TTS models skip or repeat words.)

**Tokens/words**
- Words = whitespace-separated tokens containing at least one letter or digit. Pure punctuation tokens (`—`, `-`, `…`) attach to the previous word for display.
- `char_count` counts letters and digits only (used for timing estimates).

**Warnings** (`ScriptWarning{code, message, sentence_idx}`):
- `long_sentence` (> 35 words)
- `contains_numbers` (digits present — may be read differently than expected)
- `contains_symbols` (`$ % & @ # → + =` etc.)
- `contains_url_or_email`
- `contains_emoji` (TTS usually skips them; captions may show tofu boxes)
- `very_long_script` (> 3,000 words)
- `mixed_scripts` (Latin + Devanagari mixed — fine, but voice choice matters)

**Language hint**: proportion of characters in Unicode ranges (Devanagari U+0900–U+097F → "hi"; Latin → "en" by default). Only used to pre-filter voices/fonts; never blocks.

**Acceptance tests (examples)**
- `"Hello world. This is Dr. Smith! Is it 3.5 now?"` → 3 sentences.
- `"Line one\nLine two"` → 2 sentences.
- `"Para one.\n\nPara two."` → 2 sentences, 2 paragraphs, `ends_paragraph=True` on the first.
- `"नमस्ते दुनिया। यह एक परीक्षण है।"` → 2 sentences, language_hint `hi`.
- Word count of `"Wait — what?!"` = 2.

### 5.2 Duration estimation and targeting (`narrareel/script/duration.py`) — Phase 1

#### 5.2.1 Speaking-rate model

We estimate speech time from **characters** (letters+digits), not words — it's far more accurate across short/long words.

```
speech_seconds(speed) = char_count / (cps_1x(voice) × speed_effect(speed))
```

- `cps_1x(voice)`: characters per second at 1.0× for that voice.
  - **Default** (before calibration): 14.0 cps for English (~150–165 wpm), 12.0 cps for Hindi. ⚠️ VERIFY defaults against real measurements in Phase 1 and update this line.
  - **Calibrated**: the first time a voice is used (or on preview), we synthesize the fixed calibration paragraph (`assets/calibration/en.txt`, ~60 words) and measure. Stored in `cache/calibration.json` keyed by `(engine, voice_id)`.
  - Better still: after every real generation we know the exact speech time per sentence → update the calibration with a running average. The estimate gets more accurate the more the user uses a voice.
- `speed_effect(speed)`: assume linear (`= speed`) by default. Engines don't scale perfectly linearly; after calibration at 2–3 speeds we can fit it. Not needed for Phase 1 since the closed loop (5.2.4) corrects anyway.

**Pauses** (time *between* sentences, which we control because we synthesize per sentence):

| Boundary | Default | Min | Max |
|---|---|---|---|
| Between sentences | 0.35 s | 0.15 s | 1.00 s |
| Between paragraphs | 0.80 s | 0.40 s | 1.80 s |
| Lead-in (start of audio) | 0.25 s | 0.10 s | 0.50 s |
| Tail (end of audio) | 0.40 s | 0.20 s | 1.00 s |

```
pause_seconds(scale) = lead + tail + Σ boundary_default × scale   (each clamped to [min, max])
total(speed, scale) = speech_seconds(speed) + pause_seconds(scale)
```

#### 5.2.2 Quality zones for speed

See the table in Section 3.2. Implemented as a pure function `speed_quality(speed) -> "natural" | "noticeable" | "strong" | "not_recommended"` with the thresholds 0.90/1.15, 0.80/1.30, 0.70/1.50.

#### 5.2.3 Planning algorithm

Input: analysis, voice calibration, target `T` (seconds) or none.

```
est_1x = total(speed=1.0, scale=1.0)

if T is None:
    return plan with one option per preset speed (0.75, 1.0, 1.25, 1.5, 2.0) showing resulting length + quality

# Option A — edit the script (always offered when |T - est_1x| > 3% of T)
words_per_second = word_count / est_1x
words_delta = round((T - est_1x) × words_per_second)       # + add / - cut
→ DurationOption(kind="edit_script", speed=1.0, pause_scale=1.0, words_delta, quality="natural")

# Option B — adjust delivery (pauses first, then speed)
if T > est_1x:     # need MORE time
    scale = largest pause scale ≤ max that is needed (stop when pauses reach their max)
    remaining = T - total(1.0, scale)
    speed = speech_seconds(1.0) / (speech_seconds(1.0) + remaining)   # slow down only for what's left
else:              # need LESS time
    scale = smallest pause scale ≥ min that is needed
    remaining = total(1.0, scale) - T
    speed = speech_seconds(1.0) / (speech_seconds(1.0) - remaining)
speed = clamp(speed, 0.5, 2.0)
→ DurationOption(kind="adjust_delivery", speed, pause_scale=scale, quality=speed_quality(speed))

# Option C — speed only (for people who just want "make it fit")
speed = (speech_seconds(1.0)) / (T - pause_seconds(1.0))
→ DurationOption(kind="speed_only", ...)

recommended = B if B.quality in {natural, noticeable} else A
```

If `T - pause_seconds(min)` ≤ 0 (target shorter than the pauses alone, e.g. 5 s target for a 700-word script), only Option A is valid; B/C are marked `not_recommended` with message "This script can't fit in 0:05. Cut about N words."

**Worked example** (numbers rounded): 742 words, 4,100 chars, 38 sentences, 6 paragraphs, voice at 14 cps.
- speech_1x = 4100 / 14 = 292.9 s
- pauses_1x = 0.25 + 0.40 + 32×0.35 + 5×0.80 = 15.85 s → est_1x ≈ 308.7 s ≈ **5:09**
- Target 6:00 (360 s), difference +51.3 s
  - A: words/sec = 742 / 308.7 = 2.40 → add ≈ **123 words**
  - B: pauses to max: 0.5 + 1.0 + 32×1.0 + 5×1.8 = 42.5 s (+26.7 s). Remaining 24.6 s → speed = 292.9 / (292.9 + 24.6) = **0.92×** 🟢 natural → recommended
  - C: speed = 292.9 / (360 − 15.85) = **0.85×** 🟡 noticeable
- Target 4:00 (240 s), difference −68.7 s
  - A: cut ≈ **165 words**
  - B: pauses to min: 0.1 + 0.2 + 32×0.15 + 5×0.4 = 7.1 s (−8.75 s). Remaining 59.95 s → speed = 292.9 / (292.9 − 59.95) = **1.26×** 🟡 noticeable
  - C: speed = 292.9 / (240 − 15.85) = **1.31×** 🟠 strong
  - recommended = B (noticeable is acceptable), but UI shows A prominently too.

(Unit tests encode these exact numbers.)

#### 5.2.4 Closed-loop correction (hitting the target for real)

Estimates are never perfect. Because we synthesize **sentence by sentence**, after synthesis we know the *exact* speech duration of every sentence, so we can hit the target almost exactly:

1. Synthesize all sentences at the plan's speed → measure `speech_actual = Σ sentence durations` (after trimming leading/trailing silence from each clip).
2. `pause_budget = T − speech_actual`.
3. If `pause_budget` fits within `[Σ min pauses, Σ max pauses]` → distribute it across boundaries proportionally to their defaults (paragraph breaks get ~2.3× a sentence break), clamped per boundary. Done — exact length, no quality loss.
4. If it doesn't fit, apply a small global tempo change with ffmpeg `atempo` (pitch-preserving) of at most ±6% to the speech, then redo step 3.
5. If still off by > 2% → finish anyway and report: "Your video is 6:08 (target 6:00). Cut ~20 words for an exact fit."

No target set → use default pauses (scale from the plan) and skip correction.

#### 5.2.5 Duration string parsing

`parse_duration("6m") = 360`, `"6:00" = 360`, `"1:02:00" = 3720`, `"90s" = 90`, `"90" = 90`, `"1m30s" = 90`, `"1.5m" = 90`. Invalid → `ScriptError` with message. `format_duration(308.7) = "5:09"`.

### 5.3 Voice engines — Phase 1 (Edge, Kokoro), Phase 4 (Chatterbox)

#### 5.3.1 Engine interface (`engines/base.py`)

```python
class EngineCapabilities(BaseModel):
    offline: bool                  # works without internet (after model download)
    native_word_timing: bool       # engine returns word boundaries
    native_speed: bool             # engine can change speed itself
    energy_control: Literal["none", "basic", "expressive"]
    cloning: bool
    languages: list[str]
    needs_gpu: Literal["no", "recommended", "yes"]

class EngineStatus(BaseModel):
    available: bool
    reason: str | None             # e.g. 'Install with: pip install "narrareel[offline]"'
    needs_download: bool           # model not downloaded yet
    download_size_mb: int | None

class SentenceAudio(BaseModel):
    samples: np.ndarray            # float32 mono  (arbitrary_types_allowed)
    sample_rate: int
    words: list[tuple[str, float, float]] | None   # (word, start, end) relative to clip, if native

class TTSEngine(Protocol):
    id: str
    display_name: str
    capabilities: EngineCapabilities

    def status(self) -> EngineStatus: ...
    def list_voices(self) -> list[VoiceInfo]: ...
    def prepare(self, progress=None) -> None: ...              # download/load models
    def synthesize(self, text: str, voice: VoiceSelection) -> SentenceAudio: ...
```

- Engines synthesize **one sentence at a time**. The pipeline (5.6) handles concatenation, pauses and timing. This keeps engines tiny and makes adding new engines easy (a good-first-issue category).
- Async engines (Edge) wrap their async API internally with a private event loop running in a worker thread — callers stay synchronous. (Avoids the current `asyncio.run()`-inside-Streamlit fragility, and works inside FastAPI's threadpool.)
- `registry.py` holds `ENGINES = {"edge": "narrareel.engines.edge:EdgeEngine", "kokoro": ..., "chatterbox": ...}` and imports lazily. `get_engine(id)`, `available_engines()`.

#### 5.3.2 Edge engine (`engines/edge.py`) — online, default for quality

- Library: `edge-tts` (LGPL-3.0, ~12.2k stars). Uses Microsoft Edge's online "Read aloud" service. **Unofficial** — may change or rate-limit. UI labels it "Online (Microsoft)".
- API facts (from edge-tts source, v7.2.x): `Communicate(text, voice, rate="+0%", volume="+0%", pitch="+0Hz", boundary="WordBoundary" | "SentenceBoundary")`. Default boundary is `SentenceBoundary`; **we must pass `boundary="WordBoundary"`** to get per-word timing. `stream()` yields dicts: `{"type": "audio", "data": bytes}` and `{"type": "WordBoundary", "offset": int, "duration": int, "text": str}`. Offsets/durations are in 100-nanosecond ticks → seconds = ticks / 10,000,000. ⚠️ VERIFY tick unit with a real call in Phase 1 tests.
- Output is MP3 bytes → decode to float32 via ffmpeg (`audio/process.py`).
- Speed mapping: `rate = f"{round((speed - 1) * 100):+d}%"`.
- Energy mapping (basic): energy 0.0→1.0 maps to `pitch` −4 Hz → +6 Hz and `volume` −5% → +5%, plus a subtle rate nudge of −3% → +4%. (Small, safe ranges; large values sound robotic.) Plus post-processing in 5.4.
- Voices: curated list (the 15 from the prototype, with accents/genders) shown first; full list via `edge_tts.list_voices()` cached for 24 h in `cache/edge_voices.json`, filtered by language.
- Reliability: 3 retries with exponential backoff (1 s, 2 s, 4 s) per sentence; clear network error message; fail the job after retries.
- Concurrency: synthesize up to 4 sentences in parallel (async gather with a semaphore) to speed up long scripts. ⚠️ VERIFY the service tolerates 4 concurrent requests without throttling; fall back to 2.

#### 5.3.3 Kokoro engine (`engines/kokoro.py`) — offline, optional extra `narrareel[offline]`

- Model: **Kokoro-82M**, weights **Apache-2.0** (hexgrad/Kokoro-82M on Hugging Face, ~10.8M downloads).
- Runtime: **`kokoro-onnx`** (MIT, ~2.8k stars, v0.6.1, Python 3.10–3.13, uses onnxruntime — no PyTorch). Chosen over the official `kokoro` package because that requires Python < 3.13 and PyTorch.
- ⚠️ **Licence note:** `kokoro-onnx` depends on **`phonemizer` (GPL-3.0+)** and `espeakng-loader` (MIT wrapper that loads **espeak-ng, GPL-3.0**) for text-to-phoneme conversion. This is why Kokoro is an **optional extra**, not a core dependency, and why it's documented in `THIRD_PARTY_LICENSES.md`. Our own code is never copied into or from these; we only import them at runtime. (See Section 6.3.)
- Model files: `kokoro-v1.0.onnx` (+ an int8 quantized variant) and `voices-v1.0.bin`, downloaded from the kokoro-onnx GitHub releases on first use into `~/.narrareel/models/kokoro/`. ⚠️ VERIFY exact URLs, sizes (fp32 ≈ 300 MB, int8 ≈ 90 MB — approximate) and SHA-256 hashes; pin them in code. Default to int8 for CPU speed if quality is acceptable (test both).
- Download UX: explicit consent ("NarraReel needs to download the offline voice model (~90 MB). Download now?"), progress bar, resume on failure, SHA-256 check.
- API (kokoro-onnx): `Kokoro(model_path, voices_path)`, `samples, sr = kokoro.create(text, voice="af_heart", speed=1.0, lang="en-us")`. ⚠️ VERIFY signature against v0.6.1.
- Voices: read voice names from `voices-v1.0.bin` (`kokoro.get_voices()` ⚠️ VERIFY). Naming convention: first letter = language (`a` American English, `b` British English, `h` Hindi, …), second = gender (`f`/`m`). Map to `VoiceInfo` with readable names ("Heart — US female").
- Speed: native `speed` parameter.
- Energy: none native → post-processing only (5.4).
- Word timing: kokoro-onnx doesn't expose word timestamps (⚠️ VERIFY) → use **estimated** timing (5.7.2), or **aligned** timing if `narrareel[align]` is installed.
- Performance: load the model once per process and keep it (registry caches engine instances).

#### 5.3.4 Chatterbox engine (`engines/chatterbox.py`) — cloning, Phase 4, optional extra `narrareel[clone]`

- Repo `resemble-ai/chatterbox` (~26.8k stars). **Code MIT, weights MIT** (`ResembleAI/chatterbox`, `ResembleAI/chatterbox-turbo` on Hugging Face). Package `chatterbox-tts` 0.1.7 (MIT).
- Model family (from the README):
  - **Chatterbox (original, 500M, English)** — has `exaggeration` and `cfg_weight` controls. Defaults `exaggeration=0.5, cfg_weight=0.5`; README tip for expressive speech: `cfg_weight≈0.3`, `exaggeration≈0.7+`. Higher exaggeration speeds speech up; lower cfg compensates.
  - **Chatterbox-Turbo (350M, English)** — lower compute/VRAM, single-step decoder, native paralinguistic tags `[laugh]`, `[chuckle]`, `[cough]`.
  - **Chatterbox-Nano (110M, English)** — same architecture as Turbo, README claims ~3× faster than real time on 8 CPU cores.
  - **Chatterbox Multilingual V3 (500M, 23+ languages)**.
- Every output includes Resemble AI's **Perth watermark** (imperceptible, detectable). We keep it on and mention it in docs — it's a responsible-AI feature we're proud of, not something to hide.
- Usage (from README, original model): `model = ChatterboxTTS.from_pretrained(device=...)`; `wav = model.generate(text, audio_prompt_path="reference.wav", exaggeration=..., cfg_weight=...)`; sample rate `model.sr`. Turbo: `ChatterboxTurboTTS.from_pretrained(device=...)`; Nano: same class with `nano=True`. ⚠️ VERIFY exact generate() kwargs per model at Phase 4 start.
- Model choice in UI: "Best quality (GPU)" → original/Turbo; "Fast on CPU" → Nano; "Other languages" → Multilingual V3.
- Speed: not native → synthesize at 1.0 and apply `atempo` (5.5).
- Energy: maps to exaggeration/cfg_weight (5.4). This is the **real** answer to "AI voice has no energy".
- Dependencies are heavy: `torch==2.6.0`, `torchaudio==2.6.0`, `transformers==5.2.0`, `diffusers==0.29.0`, `librosa==0.11.0` (pins from PyPI metadata for Python < 3.14). These pins may conflict with other packages → recommend installing the clone extra in its own venv or using Docker/Colab. Verified 2026-10-10 on Windows + Python 3.13 (needs `setuptools<81`, see D26).

#### 5.3.5 Other engines (backlog, evaluated 2026-10-10)

| Engine | Code licence | Weights licence | Decision |
|---|---|---|---|
| CosyVoice 3 (QwenAudio/CosyVoice, ~23.9k★) | Apache-2.0 | Apache-2.0 (`FunAudioLLM/Fun-CosyVoice3-0.5B-2512`) | ✅ Allowed — backup cloning engine, good multilingual |
| VibeVoice (microsoft/VibeVoice, ~54.7k★) | MIT | MIT (`microsoft/VibeVoice-1.5B`) | ✅ Allowed — candidate for long-form (10-min) narration |
| OmniVoice (k2-fsa/OmniVoice, ~14.4k★; powers VoiceStudio) | Apache-2.0 | **not declared on HF card** | ⏸ Blocked until weights licence is verified |
| Zonos (Zyphra, ~7.2k★) | Apache-2.0 | Apache-2.0 | ✅ Allowed (less active) |
| NeuTTS Air (neuphonic) | other | Apache-2.0 (gated) | ⏸ Check code licence |
| IndexTTS-2 | other | not declared | ⏸ Blocked until verified |
| F5-TTS | MIT | **CC-BY-NC-4.0** | ❌ Non-commercial weights |
| XTTS-v2 (Coqui) | MPL-2.0 | **Coqui Public Model License (non-commercial)** | ❌ |
| Fish Speech / OpenAudio | other | **CC-BY-NC-SA-4.0** | ❌ |
| Spark-TTS | Apache-2.0 | **CC-BY-NC-SA-4.0** | ❌ |
| Seed-VC | GPL-3.0 | — | ❌ for core (copyleft); maybe external later |
| VoiceStudio (debpalash) | **AGPL-3.0** | per-model | Only as an optional **external service** over HTTP (`VOICESTUDIO_URL`). Never copy code. ⚠️ VERIFY it exposes a TTS/clone HTTP endpoint (its documented API covers transcription). |

### 5.4 Energy

"Energy" is one slider (0.0 Calm · 0.5 Normal · 1.0 Hype). What it does depends on the engine:

| Engine | Energy implementation | Honesty level in UI |
|---|---|---|
| Chatterbox | `exaggeration = 0.3 + 0.6 × e` (0.3 → 0.9); `cfg_weight = 0.6 − 0.3 × e` (0.6 → 0.3) | "Real expressive control" |
| Edge | small pitch/volume/rate offsets (5.3.2) + post-processing | "Subtle" |
| Kokoro | post-processing only | "Subtle" |

**Post-processing chain for "energy" (all engines, ffmpeg filters):**
- Gentle compression (`acompressor`) — more consistent, "punchier" voice; ratio rises with energy.
- Presence EQ boost around 3–5 kHz (`equalizer`) — up to +3 dB at high energy.
- Light high-pass at ~80 Hz to remove rumble.
- Final loudness normalisation (5.6) — always on.

**Tip shown in the cloning flow:** "Read the sample paragraph with the energy you want. Your clone copies how you speak, not just how you sound."

All mappings are constants in one place (`engines/energy.py` or inside each engine) so they can be tuned by ear later.

### 5.5 Speed application

1. If the engine supports native speed (Edge, Kokoro) → use it (sounds more natural than post-stretching).
2. Otherwise (Chatterbox) → synthesize at 1.0 and apply `atempo` to each sentence clip. `atempo` accepts 0.5–100 in recent ffmpeg; we chain filters for extreme values anyway (`atempo=2.0,atempo=1.25`) for older builds.
3. Word timings from native engines are already at the final speed. For `atempo`-stretched clips, timings are divided by the tempo factor.
4. Closed-loop correction (5.2.4) may apply an extra ±6% `atempo` to the whole narration; all timings are scaled the same way.

### 5.6 Audio pipeline (`narrareel/pipeline/speak.py`, `audio/process.py`) — Phase 1

```
ScriptAnalysis + VoiceSelection + DurationPlan
   │
   ├─ for each synthesis unit (sentence or split long sentence), in parallel where allowed:
   │     engine.synthesize(text) → SentenceAudio (float32, engine sample rate)
   │     resample to 48 kHz mono (ffmpeg or numpy via ffmpeg decode)
   │     trim leading/trailing silence (threshold −45 dBFS, keep 30 ms padding)
   │     apply tempo if needed (5.5)
   │     save sentences/NNNN.wav  (cache: hash(text, voice, speed, energy) → reuse on re-runs)
   │
   ├─ compute pauses (5.2.4 closed loop)
   ├─ assemble in numpy: lead + s0 + p0 + s1 + p1 + … + tail   (exact sample positions → exact timings)
   ├─ energy post-processing chain (5.4)
   ├─ loudness normalise to −14 LUFS integrated, −1 dBTP true peak (social-media standard; two-pass loudnorm)
   │     ⚠️ VERIFY target: −14 LUFS is common for YouTube/Spotify; some creators prefer −16. Make it a setting.
   ├─ write voice.wav (48 kHz, 16-bit PCM, via stdlib `wave`) and voice.mp3 (ffmpeg libmp3lame, 192 kbps)
   └─ word timings (5.7) → words.json; basic captions → captions.srt
```

Why numpy assembly instead of ffmpeg concat: we know every sample offset, so word timings are exact, and it's simple. Memory: 10 min × 48 kHz × 4 bytes ≈ 115 MB float32 — fine.

Sentence caching means changing only captions, or only the pause scale, never re-synthesizes voice.

### 5.7 Word timing (`narrareel/timing/`) — Phase 1

Every `WordTiming` maps to a script token (`token_idx`), so captions always show the user's original text and punctuation, even when the engine reports different text.

#### 5.7.1 Native (Edge)

- Engine returns `(word, start, end)` per spoken word for each sentence clip.
- Map engine words to script tokens in that sentence with a sequence matcher on normalised text (`difflib.SequenceMatcher` over `norm` lists). Edge's boundary text usually excludes punctuation and may expand numbers ("2026" → "twenty twenty-six" spoken as multiple boundaries ⚠️ VERIFY behaviour) — unmatched engine words are merged into the nearest matched token; unmatched script tokens get interpolated times.
- Offset by the clip's position in the final audio (and tempo factor, if any).

#### 5.7.2 Estimated (no extra dependencies; used for Kokoro when align isn't installed)

Because we synthesize per sentence and trim silence, we know each sentence's exact start/end. Inside a sentence, distribute time by weights:

```
weight(token) = syllable_estimate(token) + 0.5 × (token ends with , ; :) + 1.0 × (token ends with . ! ? …)
```

- `syllable_estimate`: vowel-group count for Latin words (min 1); for Devanagari, count of consonant+matra clusters ≈ characters/2 (min 1); numbers: digits count × 1.5.
- Punctuation weight models the small pause after commas and before the next clause.
- Accuracy is decent (sentence-anchored, so drift can't accumulate across sentences) — typically within ~150 ms for short sentences. ⚠️ VERIFY with Edge native timings as ground truth in tests.

#### 5.7.3 Aligned (optional extra `narrareel[align]`)

- `faster-whisper` (MIT, ~25.8k stars) with `word_timestamps=True`, model `base` or `small` on CPU (int8). Model downloads on first use (~150–500 MB ⚠️ VERIFY).
- Run per sentence clip (short, fast, and the language is known) → recognised words with times → align to script tokens with the same sequence-matcher approach → fill gaps by interpolation.
- Used automatically for Chatterbox/Kokoro when installed; "Precise caption timing" toggle in settings.
- Alternative if needed: `whisperX` (BSD-2, ~24.5k stars) for phoneme-level alignment. Avoid `whisper-timestamped` (AGPL).

#### 5.7.4 Timing quality checks

- Monotonic: `start[i] ≤ end[i] ≤ start[i+1]` (fix overlaps by clamping).
- Minimum word duration 60 ms (very short words get stretched into neighbouring gaps).
- A word may not cross a sentence boundary.

### 5.8 Voice cloning (Phase 4) — the headline feature

#### 5.8.1 User flow

1. **Intro card:** "Clone your voice in about a minute. Your recording stays on your computer."
2. **Record or upload.** Browser recording via `MediaRecorder` (WebM/Opus) in React; or upload WAV/MP3/M4A. Target length 15–30 s (minimum 8 s, maximum 60 s — longer is trimmed to the cleanest 30 s).
3. **Guided script to read** (shown on screen), written to cover varied sounds and an energetic delivery. E.g.:
   > "Hey, welcome back! Today I'm going to show you something really exciting. It's quick, it's simple, and honestly, it changed how I work. Let's jump right in — you're going to love this."
   Plus a Hindi version and a calm version. Tip: "Read it the way you want your videos to sound."
4. **Quality check** (instant, server-side):
   - Duration in range
   - Not clipping (peak < −0.5 dBFS on > 99.9% of samples)
   - Loud enough (RMS > −35 dBFS)
   - Noise floor (estimate from quietest 10% frames; warn if > −50 dBFS: "Background noise detected — try a quieter room")
   - Mostly speech (voice activity ratio > 60%)
   Show ✅/⚠️ per check; allow continuing with warnings.
5. **Consent (required checkbox):** "This is my voice, or I have explicit permission from the person whose voice this is. I won't use it to impersonate or deceive anyone." Stored in `profile.json` with timestamp.
6. **Name it** ("My energetic voice").
7. **Create** → preprocess (5.8.2) → generate a sample sentence → play it. "Sounds right? Save." / "Try again".
8. Voice appears under **My voices** in Step 3, usable like any other voice.

#### 5.8.2 Preprocessing pipeline

1. Decode to mono float32.
2. High-pass 70 Hz; optional light denoise (ffmpeg `afftdn`, conservative) — test whether it helps Chatterbox or hurts it; default off if it hurts.
3. Trim leading/trailing silence; collapse internal silences > 0.6 s to 0.3 s.
4. Loudness normalise to −20 LUFS (reference clips shouldn't be hot).
5. Pick the best continuous 10–30 s window (highest speech ratio, no clipping).
6. Resample to the engine's expected rate (Chatterbox: `model.sr`, ⚠️ VERIFY; store reference at 24 kHz or 48 kHz and let the engine resample).
7. Save `voices/<id>/reference.wav`.

Zero-shot: there is **no training step**. A "voice" is just a reference clip + settings. That's why cloning is fast and why profiles are tiny and portable (export/import as a zip).

#### 5.8.3 Generation with a cloned voice

- Per sentence (like other engines). Long scripts: Chatterbox quality is best on short inputs; our sentence splitting (5.1) keeps inputs short.
- Seed control: fix a random seed per job for consistent voice across sentences (⚠️ VERIFY Chatterbox exposes/needs seeding via torch).
- Consistency check (optional, later): compare speaker embedding of each sentence to the reference; regenerate outliers.
- GPU strongly recommended for the 500M models; Nano for CPU users.

#### 5.8.4 Hardware matrix and messaging

| User hardware | Recommendation shown |
|---|---|
| NVIDIA GPU (CUDA) | "Best quality" model, fast |
| Apple Silicon (MPS) | Turbo/original on MPS ⚠️ VERIFY MPS support |
| CPU only | Nano model ("works on CPU, slower") or "Use the free Colab notebook (GPU)" |

#### 5.8.5 Google Colab notebook (`notebooks/NarraReel_Colab.ipynb`)

- One-click "Open in Colab" badge in README.
- Cells: install `narrareel[clone,align]` → upload reference recording + script → choose settings → generate → download voice.mp3 + words.json + (optionally) the rendered video.
- Or: run `narrareel serve` in Colab with a public tunnel for the full UI. ⚠️ VERIFY Colab's current terms about running web UIs/tunnels before recommending this; default to the plain-cells approach.

#### 5.8.6 Ethics and safety

- Consent checkbox + stored consent record (5.8.1).
- Perth watermark kept on for Chatterbox output.
- Docs section "Responsible use": only clone voices you own or have permission for; disclose AI narration where platforms require it (many platforms require labelling AI-generated/synthetic content ⚠️ VERIFY current platform rules before writing that section).
- No feature to clone from a YouTube link or someone else's video.

### 5.9 Captions (Phase 2)

#### 5.9.1 Chunking (`captions/chunk.py`)

Input: `list[WordTiming]` + `CaptionStyle`. Output: `list[CaptionChunk{lines: list[list[word_idx]], start, end}]`.

Rules, in order:
1. Never cross a sentence end — a new sentence starts a new chunk.
2. Break when there's a pause > 0.35 s between words.
3. Max `words_per_chunk` (style setting, 1–8; "One Word" preset = 1).
4. Max characters per line (derived from format width, font size and font metrics measured with Pillow) and max lines (1–2).
5. Avoid orphans: don't leave a single short word (≤ 3 chars) alone at the end of a chunk if it can join the previous or next.
6. Prefer breaking after punctuation (`,` `;` `:` `—`).
7. Chunk `start` = first word start; `end` = min(last word end + 0.15 s hold, next chunk start). Minimum on-screen time 0.4 s (merge or extend if shorter).

#### 5.9.2 Caption style model and presets (`captions/styles.py`, `presets/styles/*.json`)

```json
{
  "id": "bold-pop",
  "name": "Bold Pop",
  "version": 1,
  "font": { "family": "Montserrat", "weight": 900, "size": 88, "uppercase": true, "letter_spacing": 0 },
  "colors": {
    "text": "#FFFFFF",
    "highlight": "#FFE600",
    "outline": "#000000",
    "shadow": "#000000AA",
    "box": null
  },
  "outline_width": 6,
  "shadow_offset": 3,
  "layout": { "words_per_chunk": 3, "max_lines": 2, "position": "lower_middle", "offset_y": 0, "line_spacing": 1.05 },
  "highlight": { "mode": "word", "scale": 1.15, "box": false },
  "animation": { "in": "pop", "duration_ms": 120 },
  "emphasis": { "enabled": false, "color": "#00E5FF", "scale": 1.25 }
}
```

Presets to ship in Phase 2:

| Preset | Look |
|---|---|
| **Bold Pop** | Heavy uppercase font, thick black outline, active word yellow + slightly bigger, words pop in |
| **Karaoke Highlight** | Whole chunk visible, active word changes colour |
| **Boxed** | Active word gets a coloured rounded box behind it |
| **One Word** | One big word at a time, centred, punchy |
| **Minimal** | Clean sans, sentence case, small shadow, no highlight |
| **Neon** | Bright coloured text with glow-like soft outline |
| **Keyword Emphasis** | Normal text; important words (long/capitalised/numbers or user-marked with `*word*`) appear bigger and coloured |
| **Subtitle Classic** | Bottom, white with black box — for YouTube/educational |

Validation: JSON Schema in `presets/styles/schema.json`; CI validates every preset. Community can contribute presets via PR (good-first-issue).

#### 5.9.3 Fonts (`captions/fonts.py`, `assets/fonts/`)

**Bundled set** (all from Google Fonts; each family's licence file is shipped next to the font; licences ⚠️ VERIFY at download time by `scripts/fetch_fonts.py`):

| Family | Vibe | Expected licence |
|---|---|---|
| Montserrat (Black, ExtraBold, Bold) | Bold — the classic Reels caption font | OFL |
| Anton | Bold/condensed impact | OFL |
| Bebas Neue | Tall condensed headline | OFL |
| Poppins (Bold, SemiBold) | Clean modern | OFL |
| Oswald | Condensed bold | OFL |
| Archivo Black | Heavy | OFL |
| Bangers | Comic/fun | OFL |
| Luckiest Guy | Fun, rounded | Apache-2.0 |
| Lilita One | Friendly bold | OFL |
| Permanent Marker | Handwritten | Apache-2.0 |
| Inter (Bold) | Clean UI-style | OFL |
| Rubik (Bold) | Rounded clean | OFL |
| Kanit (Bold) | Sporty | OFL |
| Roboto Condensed | Neutral condensed | ⚠️ VERIFY (Apache-2.0 historically) |
| Noto Sans Devanagari (Bold) | Hindi/Marathi captions | OFL |

Size budget: keep total bundled fonts < 15 MB; only ship the weights we use.

`assets/fonts/manifest.json` entry:

```json
{ "id": "montserrat-black", "family": "Montserrat", "style": "Black", "weight": 900,
  "file": "Montserrat/Montserrat-Black.ttf", "license": "OFL-1.1", "license_file": "Montserrat/OFL.txt",
  "source": "https://fonts.google.com/specimen/Montserrat", "tags": ["bold", "popular"], "scripts": ["latin"] }
```

**Font family names matter for libass:** ASS styles reference fonts by *family name* (from the font's name table), not by file name. `fonts.py` reads `(family, style)` with Pillow `ImageFont.truetype(path).getname()` and stores it; the ASS writer uses that exact family name and sets `Bold`/weight flags accordingly. Each render job copies only the needed font files into `jobs/<id>/fonts/` and passes `fontsdir=fonts` to libass, so system fonts can't silently substitute.

**User fonts:** upload `.ttf`/`.otf` → validate by loading with Pillow → read family name → copy to `~/.narrareel/fonts/user/` → appears in the picker tagged "Yours". (User is responsible for their font's licence; show a one-line note.)

**Font previews:** `GET /api/fonts/{id}/preview.png?text=...` renders sample text with Pillow (cached on disk). The picker grid uses these.

**Script coverage check:** if the script contains Devanagari and the chosen font lacks those glyphs (check with Pillow `font.getmask` / cmap via fontTools ⚠️ decide), warn: "This font can't show Hindi characters. Try Noto Sans Devanagari."

**Emoji:** libass has limited colour-emoji support → strip emoji from captions by default with a toggle "Keep emoji (may not render)". ⚠️ VERIFY libass behaviour on the gyan.dev build.

#### 5.9.4 ASS generation (`captions/ass.py`)

Why ASS (Advanced SubStation Alpha): it supports per-word colours, outlines, shadows, boxes, positioning, scaling and simple animations, and ffmpeg/libass renders it in one fast pass. It's also a standard file editors can import.

Header essentials:

```
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2            ; we do our own line breaks
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Montserrat,88,&H00FFFFFF,&H0000E6FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,80,80,520,1
```

- Colours are `&HAABBGGRR` (alpha first, 00 = opaque; **blue-green-red order**). `colors.py` converts `#RRGGBB[AA]` correctly — classic bug source, unit-test it.
- `Alignment` uses numpad layout (2 = bottom-centre, 5 = middle-centre, 8 = top-centre). We mostly use 2 + `MarginV`, or explicit `\pos(x,y)` with `\an5`.
- `BorderStyle` 1 = outline + shadow; 3 = opaque box (for "Subtitle Classic").

**Highlight rendering strategy:** for each chunk, emit one `Dialogue` event **per word interval** (from that word's start to the next word's start), containing the full chunk text where the active word has override tags (`{\c&H0000E6FF&\fscx115\fscy115}word{\r}`). This gives exact control of colour, scale, box and animation per word, and is easy to reason about. (Alternative: karaoke `\k`/`\kf` tags — simpler but only colour sweep; keep as an option for "Karaoke Highlight".)

**Animations** via override tags:
- Pop: `{\fscx80\fscy80\t(0,120,\fscx100\fscy100)}` on chunk entry; active word `\t(0,80,\fscx115\fscy115)`.
- Fade: `{\fad(80,60)}`.
- Bounce: two chained `\t` transforms (scale up then settle).
- Box behind active word: render a second layer with `BorderStyle=3`/`\3c` box colour, or draw with `\p1` vector drawing. ⚠️ Decide the cleanest approach while implementing; test visually.

**Keyword emphasis:** words wrapped in `*asterisks*` in the script are emphasis words (asterisks removed from TTS input and captions). Auto mode (optional): numbers, words ≥ 8 chars, ALL-CAPS words.

**Escaping:** escape `{`, `}`, `\` in user text; replace newlines with `\N`.

#### 5.9.5 SRT (`captions/srt.py`) — basic version in Phase 1

Standard SRT from chunks (sentence-based chunks with max ~42 chars/line, 2 lines) for YouTube upload and editors. Times `HH:MM:SS,mmm`. Phase 1 uses a simple chunker; Phase 2 reuses `chunk.py`.

### 5.10 Formats (Phase 2) — `presets/formats/*.json`

| Id | Name | Size | Default caption position | Notes |
|---|---|---|---|---|
| `reels` | Reels / TikTok / Shorts | 1080×1920 (9:16) | lower-middle (~62% height) | Keep text out of top ~12% and bottom ~20% (platform UI) and right ~10% (buttons) ⚠️ VERIFY exact safe zones per platform |
| `youtube` | YouTube | 1920×1080 (16:9) | bottom (MarginV ~90) | Subtitle Classic default |
| `square` | Instagram post | 1080×1080 (1:1) | lower-middle | |
| `portrait` | Instagram portrait | 1080×1350 (4:5) | lower-middle | |
| `audio` | Audio only | — | — | Exports voice + SRT only |

Frame rate: 30 fps default (smoother caption pops than 24; small file cost). Option 60.

The safe-zone overlay can be toggled in the preview ("Show platform UI areas").

### 5.11 Rendering (`render/ffmpeg_render.py`) — Phase 2

All rendering is **one ffmpeg command**. Run ffmpeg with `cwd=job_dir` and **relative file names** — this avoids the Windows drive-letter colon problem in filter arguments (`subtitles=C:\...` breaks; `subtitles=captions.ass` works).

**Solid background → MP4**
```
ffmpeg -y -f lavfi -i "color=c=0x101010:s=1080x1920:r=30:d=DURATION" -i voice.wav \
  -vf "subtitles=captions.ass:fontsdir=fonts" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -shortest -movflags +faststart output.mp4
```

**Transparent overlay → WebM (VP9 + alpha)**
```
ffmpeg -y -f lavfi -i "color=c=black@0.0:s=1080x1920:r=30:d=DURATION,format=rgba" -i voice.wav \
  -vf "subtitles=captions.ass:fontsdir=fonts:alpha=1,format=yuva420p" \
  -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 -auto-alt-ref 0 \
  -c:a libopus -b:a 128k -shortest output.webm
```
⚠️ VERIFY that libass preserves alpha on a transparent lavfi source with this build (the `alpha=1` option of the subtitles filter exists in recent ffmpeg; confirm). Fallback: render captions on a green/black background and key, or render captions as RGBA PNG sequence — last resort.

**Transparent overlay → MOV (ProRes 4444)** — many editors (Premiere, Final Cut, DaVinci) prefer this:
```
... -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -c:a pcm_s16le output.mov
```
(Large files — warn the user.)

**Image background:** `-loop 1 -i bg.jpg` + `scale=W:H:force_original_aspect_ratio=increase,crop=W:H`.
**Video background (loop):** `-stream_loop -1 -i bg.mp4` + same scale/crop, optional blur (`gblur=sigma=20`) and darken (`eq=brightness=-0.15`) for readability.

**Progress:** add `-progress pipe:1 -nostats`, parse `out_time_ms` → fraction of `DURATION`.

**Preview frame (`render/preview.py`):** same filter graph with `-ss T -frames:v 1 preview.png`, where T is the middle of a real caption chunk. Takes well under a second — used for the live preview in Step 4.

**Performance targets:** 60 s Reel < 30 s render on a 4-core laptop; 10-min video < 4 min (libx264 `medium`; offer `veryfast` toggle). ⚠️ VERIFY by benchmark in Phase 2.

### 5.12 Export (Phase 2/3)

| File | When |
|---|---|
| `output.mp4` | solid/image/video background |
| `output.webm` / `output.mov` | transparent overlay |
| `voice.mp3`, `voice.wav` | always |
| `captions.srt`, `captions.ass` | always (ass only if video) |
| `words.json` | always (for power users/editors) |
| `project.narrareel.json` | always — script, plan, voice selection, caption config, format; re-openable |

Download names: `narrareel_<first-3-words-of-script>_<format>.<ext>` (slugified).

### 5.13 Jobs, progress, cancellation (Phase 3, `jobs/runner.py`)

- One in-process worker thread (concurrency 1 by default — ML models and GPU memory don't like parallel jobs); queue additional jobs.
- Each job: id (`YYYY-MM-DD_HHMMSS_<6 hex>`), status (`queued | running | done | failed | cancelled`), progress events stored in memory and appended to `log.txt`.
- Stage weights for overall progress: prepare 2% · voice 55% · timing 8% · captions 5% · render 30% (voice weight drops to ~20% when sentences are cached).
- Cancellation: `threading.Event` checked between sentences and passed to ffmpeg (terminate the process).
- Re-render: a job can be cloned with new caption/format settings; reuses `sentences/` and `voice.wav`.

### 5.14 HTTP API (Phase 3, FastAPI)

Base path `/api`. JSON in/out (pydantic models from 4.4). Bound to `127.0.0.1` by default.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | version, ffmpeg found, libass present |
| GET | `/api/engines` | list engines + `EngineStatus` + capabilities |
| POST | `/api/engines/{id}/prepare` | download/load model (progress via SSE on `/api/tasks/{id}/events`) |
| GET | `/api/voices?engine=&language=` | list voices |
| GET | `/api/voices/{engine}/{voice_id}/sample` | cached 5-second sample (mp3) |
| POST | `/api/analyze` | `{text, voice?}` → `ScriptAnalysis` + `DurationEstimate` |
| POST | `/api/plan` | `{text, voice, target_seconds? , speed?}` → `DurationPlan` |
| POST | `/api/preview/voice` | `{text, voice}` → short mp3 (first 1–2 sentences) |
| POST | `/api/preview/frame` | `{project, time?}` → PNG (Phase 2 renderer) |
| GET | `/api/fonts` · GET `/api/fonts/{id}/preview.png` · POST `/api/fonts` (upload) | font registry |
| GET | `/api/presets/styles` · `/api/presets/formats` · POST `/api/presets/styles` (save user preset) | presets |
| POST | `/api/jobs` | `{project}` → `{job_id}` |
| GET | `/api/jobs/{id}` | status + result file list |
| GET | `/api/jobs/{id}/events` | Server-Sent Events stream of `ProgressEvent` |
| POST | `/api/jobs/{id}/cancel` | cancel |
| POST | `/api/jobs/{id}/rerender` | new captions/format, reuse voice |
| GET | `/api/jobs/{id}/files/{name}` | download outputs |
| POST | `/api/voices/clone` (Phase 4) | multipart audio + name + consent → quality report + voice profile |
| DELETE | `/api/voices/custom/{id}` (Phase 4) | delete a cloned voice |

Security: loopback-only by default with no auth. If `--host` is not loopback, require `NARRAREEL_TOKEN` (bearer) and print a warning. CORS only enabled in dev mode (Vite dev server origin). Upload size limits (audio 25 MB, fonts 10 MB). Never execute anything from uploaded files; validate types by decoding, not by extension.

### 5.15 Frontend (Phase 3, React)

**Stack:** Vite + React + TypeScript (latest stable at setup time, pinned via `package-lock.json`). Minimal dependencies:
- `react-router` — a start screen at `/`, then one route per question (`/script`, `/length`, `/voice`, `/voice/ai`, `/voice/mine`, `/voice/sound`, `/captions`, `/export`; `/duration` redirects to `/length`, see D32) so the browser back button works. `src/flow.ts` says which step each screen belongs to and where Back and Next go.
- `zustand` — project state store, persisted to `sessionStorage` for the current tab only (wrapped in try/catch; D32).
- `@tanstack/react-query` — API calls, caching, loading states (optional; can start with plain `fetch` + hooks).
- No UI component library yet. Plain components + CSS variables.

**Theming (important for the upcoming design spec):** every colour, radius, spacing, font and shadow is a CSS custom property in `src/theme/tokens.css`, with light and dark values. Components use only tokens — no hard-coded colours. When the owner sends the design `.md`, we change tokens and component markup, not logic.

**Components (basic version):**
- `StartScreen` (new, continue, open), `Stepper` (5 steps, shows completion), `ReelRail` (preview + what the video is made of, on Captions and Make video only; D32)
- `ScriptEditor` (textarea + live counts + sentence list + warnings)
- `DurationPicker` (quick buttons, custom input, option cards with quality badges)
- `VoiceList` (filters, voice cards with ▶ sample), `SpeedEnergyControls`, `VoicePreviewButton`
- `FormatPicker`, `FontGrid` (preview images), `StylePresetGrid`, `CaptionFineTune`, `FramePreview` (phone/16:9 frame showing the server PNG)
- `ExportPanel`, `JobProgress` (SSE), `ResultDownloads`, `VideoPlayer`
- Phase 4: `VoiceRecorder` (MediaRecorder), `CloneQualityReport`, `ConsentCheckbox`

**API client:** generated TypeScript types from FastAPI's OpenAPI schema (`openapi-typescript`, MIT) so frontend/backend types never drift.

**Build & ship:** `npm run build` → `frontend/dist` → copied into `narrareel/server/static/` by the release workflow. The Python wheel contains the built UI, so end users never need Node. Dev mode: `npm run dev` (Vite on 5173, proxies `/api` to 8765) + `narrareel serve --dev`.

**Accessibility basics:** labels on all inputs, keyboard navigation through steps, visible focus, `prefers-reduced-motion` respected in preview animations.

### 5.16 CLI (`narrareel/cli.py`, Typer) — Phase 1 (core commands), grows later

```
narrareel doctor                          # python, ffmpeg/ffprobe, libass, engines, GPU, disk space
narrareel voices [--engine edge|kokoro] [--lang en]
narrareel analyze script.txt [--voice edge:en-US-JennyNeural] [--target 6m]
narrareel speak script.txt --voice edge:en-US-JennyNeural [--speed 1.1 | --target 60s] [--energy 0.7] [-o out_dir]
        → voice.mp3, voice.wav, words.json, captions.srt
narrareel make script.txt --voice ... --format reels --style bold-pop --font montserrat-black [-o video.mp4]   # Phase 2
narrareel clone recording.wav --name "My voice" --i-have-consent                                              # Phase 4
narrareel serve [--port 8765] [--open] [--dev]                                                               # Phase 3
narrareel clean [--keep 20]
```

Voice reference format everywhere: `<engine>:<voice_id>` (e.g. `kokoro:af_heart`, `custom:my-voice`).

---

## 6. Tech stack, licences, and open-source rules

### 6.1 Stack summary

| Area | Choice | Licence | Why |
|---|---|---|---|
| Language | Python 3.10–3.13 | PSF | ML ecosystem; owner's venv is 3.13 |
| Packaging | `pyproject.toml` + hatchling | MIT | Standard, simple |
| Models / validation | pydantic v2 | MIT | Shared models for API + core |
| CLI | Typer | MIT | Clean CLI with little code |
| Online TTS | edge-tts | LGPL-3.0 | Best free online voices; word boundaries |
| Offline TTS | kokoro-onnx + Kokoro-82M | MIT (+ GPL-3.0 phonemizer/espeak-ng deps) / Apache-2.0 weights | Fast CPU offline voice |
| Cloning | chatterbox-tts | MIT code + MIT weights | Energy control, CPU option, watermark |
| Alignment | faster-whisper | MIT | Precise word timing for any engine |
| Audio/video | ffmpeg (system binary) + libass | LGPL/GPL depending on build (we call it as a separate program) | Fast, one-pass rendering |
| Images | Pillow | MIT-CMU (HPND) | Font previews, text measuring |
| Numbers | numpy | BSD-3 | Audio assembly |
| Server | FastAPI + uvicorn + sse-starlette | MIT / BSD-3 / BSD-3 | Async API + SSE progress |
| Frontend | React + Vite + TypeScript, react-router, zustand | MIT | Owner's choice; huge ecosystem |
| Tests | pytest, ruff | MIT | Standard |
| Licence check | pip-licenses | MIT | CI enforcement |
| Fonts | Google Fonts families | OFL-1.1 / Apache-2.0 | Bundling allowed with licence files |

Removed: **Streamlit** and **MoviePy** (MoviePy stays only inside `legacy/` and the temporary Phase 1 bridge; dropped in Phase 2).

### 6.2 Licence policy (the rules)

1. **Our code is MIT.** Copyright line: `Copyright (c) 2026 SanTiwari07 and NarraReel contributors` (owner may replace with their full name — open question).
2. **Core install** (`pip install narrareel`) may only depend on packages under: MIT, BSD, Apache-2.0, ISC, PSF, MPL-2.0, HPND/MIT-CMU, or **LGPL** (used as an unmodified library).
3. **Optional extras** (`[offline]`, `[align]`, `[clone]`) may pull in copyleft (GPL) components *only if* they are separate packages we import at runtime, never copied into our repo, and the extra is documented in `THIRD_PARTY_LICENSES.md` with a plain-English note. Currently: `[offline]` → phonemizer (GPL-3.0+) and espeak-ng (GPL-3.0).
4. **AGPL** code (e.g. VoiceStudio) is never imported or copied. Only reachable as a separate service over HTTP, configured by the user.
5. **Model weights** must allow commercial use (MIT, Apache-2.0, or equivalent). **Never** non-commercial (CC-BY-NC*, Coqui CPML), research-only, or undeclared licences — undeclared = blocked until verified.
6. **Weights are never committed** to the repo. They're downloaded on first use from the official source, with size shown and consent asked.
7. **Fonts** must be OFL or Apache-2.0, shipped with their licence files.
8. **No hot-linked or third-party-licensed images/icons** (remove the flaticon image). Use our own logo or an MIT/ISC icon set (e.g. Tabler Icons MIT, Lucide ISC).
9. **Docker image** that bundles GPL components (espeak-ng) is fine (they're open source), but the image must include their licence texts and a pointer to their source.

### 6.3 Why GPL inside an optional extra is acceptable here (plain English)

- GPL is an open-source licence — using GPL software is fully compatible with "100% open source".
- The concern is only about *distributing a combined work*: if we copied GPL code into NarraReel, NarraReel would have to become GPL. We don't copy it; we depend on it optionally, and it's installed by the user from PyPI.
- Keeping it optional keeps the core install clean MIT-compatible, so companies with strict policies can still use NarraReel with Edge voices or Chatterbox.
- If this ever becomes a problem, the alternative is a phonemizer with a permissive licence (e.g. `misaki` is Apache-2.0, but its English path may still fall back to espeak ⚠️ VERIFY) — tracked as an open question.

### 6.4 Licence CI check

`scripts/check_licenses.py` (Phase 1):
1. Create a clean venv, `pip install .` (core only).
2. Run `pip-licenses --format=json`.
3. Fail if any package licence isn't in the allow-list (rule 2), with a readable report.
4. Separate informational report for each extra (doesn't fail, but must match `THIRD_PARTY_LICENSES.md`).

### 6.5 `THIRD_PARTY_LICENSES.md` contents

Table: component · version · licence · how we use it (core / extra / external service / model weights / font) · source URL. Updated whenever dependencies change (CI compares).

---

## 7. Phases and tasks

### Overview

| Phase | Name | Outcome |
|---|---|---|
| **1** | **Foundation** | Clean repo, `narrareel` package, Edge + Kokoro engines, real word timings, duration planning, CLI `speak` producing narration + timings + SRT, tests + CI |
| 2 | Captions & rendering | Fonts, style + format presets, ASS captions, fast ffmpeg renderer, transparent export, frame preview, `narrareel make` |
| 3 | Web app | FastAPI server, React 5-step wizard (basic styling), job progress, re-render; legacy Streamlit removed |
| 4 | Voice cloning | Chatterbox engine, recording + quality check + consent, voice profiles, energy, Colab notebook |
| 5 | Launch | README, demo GIF/video, Docker, HF Space, docs, CONTRIBUTING, issue templates, PyPI release, launch posts |
| 6+ | Backlog | See 7.6 |

---

### 7.1 Phase 1 — Foundation (DO THIS NOW)

**Goal:** a real Python package with a clean architecture that can turn a script into narration with **exact word timings** and **duration targeting**, usable from the command line, tested, with CI. The old prototype keeps working from `legacy/` until the React UI replaces it.

**Out of scope for Phase 1:** new caption styles/fonts, new renderer, web UI, cloning. (The only video output in Phase 1 is via the temporary bridge P1-15.)

#### P1-01 Repo hygiene
- [x] Add `LICENSE` (MIT, copyright line from 6.2).
- [x] Add `.gitignore`: `venv/`, `.venv/`, `__pycache__/`, `*.pyc`, `temp/`, `.narrareel/`, `*.egg-info/`, `dist/`, `build/`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `frontend/dist/`, `narrareel/server/static/`, `*.mp4`, `*.webm`, `*.mov`, `*.mp3`, `*.wav` (with `!tests/fixtures/**` exceptions), `.env`, `.DS_Store`, `Thumbs.db`.
- [x] Add `.editorconfig` (UTF-8, LF, 4-space Python, 2-space TS/JSON/YAML).
- [x] Commit the deletion of `test_gen.py` and `test_tts_timing.py`.
- [x] Commit the pending `generator.py` change (makedirs) as part of the legacy move.
- **Accept when:** `git status` is clean after a full run of the app; LICENSE exists.

#### P1-02 Move the prototype to `legacy/`
- [x] `git mv app.py generator.py utils.py legacy/`; fix imports (`from legacy.generator import ...` or run from `legacy/`).
- [x] Remove the flaticon hot-linked image from `legacy/app.py`.
- [x] Add `legacy/README.md`: "Old Streamlit prototype. Run with `streamlit run legacy/app.py`. Will be removed when the new UI ships."
- [x] Keep `requirements.txt` only for legacy (rename to `legacy/requirements.txt`).
- **Accept when:** `streamlit run legacy/app.py` still generates a video.

#### P1-03 `pyproject.toml`
- [x] Project metadata: name `narrareel`, version `0.1.0.dev0`, description, readme, license MIT, `requires-python = ">=3.10"`, classifiers, URLs.
- [x] Core dependencies: `edge-tts>=7.2`, `numpy>=1.24`, `pillow>=10`, `pydantic>=2.6`, `typer>=0.12`.
- [x] Extras:
  - `offline = ["kokoro-onnx>=0.6"]`
  - `align = ["faster-whisper>=1.1"]`
  - `clone = ["chatterbox-tts>=0.1.7"]` (Phase 4; may be left commented)
  - `server = ["fastapi>=0.110", "uvicorn[standard]>=0.29", "sse-starlette>=2", "python-multipart>=0.0.9"]` (Phase 3)
  - `legacy = ["streamlit", "moviepy>=2"]`
  - `dev = ["pytest>=8", "pytest-cov", "ruff", "pip-licenses"]`
- [x] Console script: `narrareel = "narrareel.cli:app"`.
- [x] Ruff config (line length 100, sensible rule set), pytest config (markers: `network`, `ffmpeg`, `slow`, `models`).
- **Accept when:** `pip install -e ".[dev]"` works in the existing 3.13 venv and `narrareel --help` runs.

#### P1-04 Package skeleton, config, errors
- [x] Create the `narrareel/` tree from 4.2 (only Phase 1 modules; others can be absent).
- [x] `config.py`: resolve `NARRAREEL_HOME`, create subfolders lazily, read env vars (4.6).
- [x] `errors.py`: hierarchy from 4.7.
- [x] `__init__.py` with `__version__`.
- **Accept when:** `python -c "import narrareel"` imports **without** importing edge-tts/kokoro (lazy imports verified by a test that checks `sys.modules`).

#### P1-05 Models
- [x] Implement `models.py` per 4.4 (pydantic v2; `arbitrary_types_allowed` only where numpy arrays are needed, and keep arrays out of API-facing models).
- **Accept when:** models serialise to JSON and back in tests.

#### P1-06 Script analysis
- [x] `script/analyze.py` per 5.1 (normalisation, sentences, tokens, counts, warnings, language hint).
- [x] Synthesis-unit splitting for > 60-word sentences.
- [x] Unit tests: all examples in 5.1 + abbreviations, decimals, ellipsis, Devanagari, empty/whitespace input, emoji.
- **Accept when:** tests pass; analysing a 3,000-word script takes < 50 ms.

#### P1-07 Duration planning
- [x] `script/duration.py`: `parse_duration`, `format_duration`, `speed_quality`, `estimate(analysis, cps, speed, pause_scale)`, `plan(analysis, cps, target)` per 5.2.
- [x] Calibration store: `cache/calibration.json` read/write; running-average update API.
- [x] Unit tests: worked examples from 5.2.3 (exact expected numbers), edge cases (target too short, no target, 1-sentence script).
- **Accept when:** tests pass with the numbers in this document.

#### P1-08 Engine base + registry
- [x] `engines/base.py` per 5.3.1; `engines/registry.py` with lazy loading, availability reasons, instance caching.
- [x] Voice reference parsing `engine:voice_id`.
- **Accept when:** with no extras installed, `available_engines()` shows Edge available and Kokoro unavailable with the correct install hint.

#### P1-09 Edge engine
- [x] Synthesize one sentence with `boundary="WordBoundary"`; collect audio bytes + boundaries; decode MP3 → float32 via ffmpeg.
- [x] Speed + basic energy mapping (5.3.2).
- [x] Curated voice list + full list cached 24 h.
- [x] Retries/backoff; clear network errors; bounded concurrency.
- [x] Tests: unit tests with a fake stream (no network); one `@pytest.mark.network` integration test that synthesizes "Hello world, this is a test." and checks boundaries are monotonic and within audio length; **verify the 100-ns tick unit here**.
- **Accept when:** integration test passes on the owner's machine.

#### P1-10 Kokoro engine (optional extra)
- [x] Model manager: pinned URLs + SHA-256 + sizes, consent prompt (CLI: `--yes` to skip), resumable download with progress, int8/fp32 choice.
- [x] Voice listing from the voices file → `VoiceInfo` with readable names.
- [x] Synthesize with native speed.
- [x] Tests: unit test of voice-name mapping; `@pytest.mark.models` integration test (skipped if extra not installed).
- **Accept when:** `narrareel speak` works fully offline after first download (test by disconnecting network).

#### P1-11 Audio utilities
- [x] `audio/ffmpeg.py`: locate ffmpeg/ffprobe (env → PATH → `imageio-ffmpeg` fallback if installed), run with captured stderr, `probe_duration`, `has_libass()`, version string.
- [x] `audio/process.py`: `decode_to_float32(bytes|path, sr=48000)`, `trim_silence`, `make_silence`, `assemble(clips, pauses)`, `tempo(clip, factor)`, `energy_chain(clip, energy)`, `loudnorm_two_pass(path)`, `write_wav` (stdlib `wave`), `encode_mp3`.
- [x] Tests: synthetic sine/silence arrays; ffmpeg-marked tests for decode/encode/loudnorm.
- **Accept when:** a 10-minute assembly runs in < 5 s (excluding TTS) and loudness of output is within ±1 LU of target.

#### P1-12 Word timing
- [x] `timing/native.py` (engine words → script tokens via sequence matcher, offset/tempo handling).
- [x] `timing/estimate.py` (5.7.2).
- [x] `timing/align.py` (faster-whisper, optional; lazy import; skip cleanly if missing).
- [x] Quality checks (5.7.4).
- [x] Tests: matcher with punctuation/number mismatches; estimation monotonicity; compare estimate vs Edge native on fixtures → mean absolute error reported (target < 150 ms).
- **Accept when:** `words.json` from Edge has every script word, monotonic times, and plays in sync (manual check with the SRT in VLC).

#### P1-13 Speak pipeline
- [x] `pipeline/speak.py`: analysis → plan → per-sentence synthesis (with sentence cache) → closed-loop pauses (5.2.4) → assemble → energy chain → loudnorm → wav/mp3 → timings → SRT.
- [x] Progress callback + cancel event support.
- [x] Sentence cache key = sha256(engine, voice_id, speed, energy, text, engine version).
- **Accept when:**
  - 60-second target on a ~170-word script → output length within ±2% of 60 s.
  - Re-running with only a different target re-uses cached sentences (no new TTS calls — verified by a counter/mock).

#### P1-14 Workspaces
- [x] `jobs/workspace.py`: create unique job folders (4.5), write `project.json`, `log.txt` handler, cleanup policy, `narrareel clean`.
- **Accept when:** two concurrent `speak` runs don't touch each other's files.

#### P1-15 Temporary video bridge — ⏸ skipped on purpose: the Phase 2 renderer shipped first, so the MoviePy bridge was never needed
- ⏸ `render/legacy_moviepy.py`: the prototype's Pillow+MoviePy renderer, but fed **real `WordTiming`s** and the job workspace (no fixed paths). Marked deprecated; deleted in Phase 2.
- ⏸ `narrareel make` (minimal flags: `--font`, `--size`, `--color`, `--highlight`, `--words-per-chunk`, `--position`, `--transparent`) uses it.
- **Accept when:** `narrareel make script.txt --voice edge:en-US-AvaNeural --target 30s` produces an MP4 with in-sync captions.
- (If time is short, this task may be skipped — Phase 2 replaces it.)

#### P1-16 CLI
- [x] Commands: `doctor`, `voices`, `analyze`, `speak`, `make` (bridge), `clean` (5.16).
- [x] Human-friendly output (tables for voices; plan options with quality badges as text: `[natural]`, `[noticeable]`…), `--json` flag for machine-readable output.
- **Accept when:** each command has `--help` text and at least one test using Typer's `CliRunner`.

#### P1-17 Tests + CI
- [x] `tests/unit/` for everything pure; `tests/integration/` with markers.
- [x] `.github/workflows/ci.yml`: matrix {ubuntu-latest, windows-latest} × Python {3.10, 3.12, 3.13}; install ffmpeg (apt / choco); `pip install -e ".[dev]"`; `ruff check`; `pytest -m "not network and not models"`; licence check job (6.4).
- **Accept when:** CI green on the first PR. (Met: PR #11 and the follow-up push to `main` are green.)

#### P1-18 Docs for Phase 1
- [x] `THIRD_PARTY_LICENSES.md` (6.5) for current deps.
- [x] README: rename to NarraReel, one-paragraph vision, "Status: rebuilding — Phase 1", new install + CLI usage, link to this file. (Full README is Phase 5.)
- [x] Update this file's status lines.

#### Phase 1 definition of done
- [x] All P1 tasks ticked (P1-15 optional).
- [x] On the owner's Windows machine (Python 3.13): `narrareel doctor` all green for core; `narrareel speak` works with Edge; with `[offline]`, works with Kokoro offline.
- [x] Duration target hits within ±2%.
- [x] Captions (SRT) visibly in sync for a 2-minute script.
- [x] CI green; licence check green. (GitHub run of 2026-10-10: all 6 test jobs {ubuntu, windows} x {3.10, 3.12, 3.13}, frontend and licences passed)

#### Suggested commit sequence for Phase 1
1. `chore: add MIT licence, gitignore, editorconfig; move prototype to legacy/`
2. `build: add pyproject and narrareel package skeleton`
3. `feat(script): text analysis and sentence splitting`
4. `feat(duration): estimates, target planning, speed quality`
5. `feat(audio): ffmpeg wrapper and audio processing utilities`
6. `feat(engines): engine interface, registry, Edge engine with word boundaries`
7. `feat(timing): native mapping, estimated and aligned timings`
8. `feat(pipeline): speak pipeline with closed-loop duration and caching`
9. `feat(engines): Kokoro offline engine with model manager`
10. `feat(cli): doctor, voices, analyze, speak, clean`
11. `ci: tests and licence check`
12. `docs: third-party licences, README update`

---

### 7.2 Phase 2 — Captions & rendering

- [x] P2-01 `scripts/fetch_fonts.py`: download chosen families from Google Fonts' GitHub repo, verify licence per family, write `manifest.json`, copy licence files.
- [x] P2-02 `captions/fonts.py`: registry (bundled + user), family-name extraction, previews, glyph coverage check.
- [x] P2-03 `captions/styles.py` + JSON schema + 8 presets (5.9.2); CI validates presets.
- [x] P2-04 `presets/formats/*.json` (5.10).
- [x] P2-05 `captions/chunk.py` (5.9.1) with tests.
- [x] P2-06 `captions/ass.py` + `colors.py` (5.9.4): styles, per-word highlight events, animations, emphasis, escaping; golden-file tests (compare generated `.ass` to expected).
- [x] P2-07 `render/ffmpeg_render.py`: solid/transparent(WebM, MOV)/image/video backgrounds, progress parsing, cancellation; Windows-safe relative paths.
- [~] P2-08 Verify transparent output in CapCut, DaVinci Resolve, Premiere (owner tests at least one) — record results in decision log. **Alpha verified by decoding WebM (VP9) and ProRes 4444 frames; NOT yet opened in CapCut/Premiere/DaVinci — owner to test one**
- [x] P2-09 `render/preview.py` single-frame PNG.
- [x] P2-10 `pipeline/make.py` full pipeline; `narrareel make` switches to the new renderer; delete `render/legacy_moviepy.py`; drop MoviePy.
- [x] P2-11 Exports (5.12) incl. `project.narrareel.json` load/save.
- [x] P2-12 Benchmarks (5.11 targets) → record numbers in this file. **60 s Reel renders in ~10 s, 8-minute video in ~74 s (12-core laptop, libx264 medium); see section 16**
- [x] P2-13 Visual regression: render a fixed preview frame per preset and compare a 4096-bit perceptual hash (`tests/unit/test_visual_regression.py`, hashes in `tests/golden/preview_hashes.json`). **Tolerance 15 bits; a 2 % font-size change moves ~30 bits. Hashes were generated on Linux; the first Windows CI run confirms they transfer.**
- **Done when:** `narrareel make` creates good-looking Reels in every preset and format; 60 s Reel renders in < 30 s on the owner's laptop.

### 7.3 Phase 3 — Web app (FastAPI + React)

- [x] P3-01 `server/app.py`: app factory, static serving of built UI, `/api` routes (5.14), SSE, error handlers → friendly JSON errors.
- [x] P3-02 `jobs/runner.py` (5.13).
- [x] P3-03 `narrareel serve [--open] [--dev]`.
- [x] P3-04 `frontend/` scaffold: Vite + React + TS, router, zustand store, API client generated from OpenAPI, `tokens.css` with light/dark themes.
- [x] P3-05 Steps 1–5 screens (Section 3) with basic, clean styling.
- [x] P3-06 Live preview (frame PNG) with debounce; voice samples; SSE progress; downloads; re-render.
- [x] P3-07 Draft persistence (localStorage), "Open project" (load `project.narrareel.json`).
- [~] P3-08 Release workflow builds frontend into the wheel. **release.yml written (builds UI into the wheel; wheel build and clean-venv install verified locally); not run on GitHub yet**
- [x] P3-09 Delete `legacy/` and Streamlit.
- [x] P3-10 Apply the owner's design `.md` (when received): map to tokens + component structure.
- **Done when:** a new user can go from script to downloaded video entirely in the browser UI, on Windows/macOS/Linux, with `pip install "narrareel[server]"` + `narrareel serve --open`.

### 7.4 Phase 4 — Voice cloning

- [x] P4-01 Verify Chatterbox install matrix (Windows/macOS/Linux × CPU/CUDA/MPS × Python 3.10–3.13); document results.
- [x] P4-02 `engines/chatterbox.py` (5.3.4): model variants, device selection, seed, energy mapping, atempo speed.
- [x] P4-03 Reference preprocessing + quality checks (5.8.2, 5.8.1-4).
- [x] P4-04 Voice profiles storage, list/delete/export/import.
- [x] P4-05 API endpoints + React `VoiceRecorder`, quality report, consent, naming, sample playback.
- [x] P4-06 Aligned timings default for cloned voices (if `[align]` installed), else estimated.
- [~] P4-07 Colab notebook (5.8.5) + "Open in Colab" badge. **Notebook written and its commands checked against the real CLI and a real cloning run on Windows; not run on Colab itself (owner: run it once)**
- [x] P4-08 Responsible-use doc section.
- [⏸] P4-09 (Optional) CosyVoice 3 as a second cloning engine. **optional, not started**
- **Done when:** owner records 30 s, gets a clone, generates a 60-second Reel in their own voice at "Hype" energy, and it sounds clearly more energetic than Edge/Kokoro.

### 7.5 Phase 5 — Launch

See Sections 9–11 for details.
- [x] P5-01 Rename GitHub repo to `NarraReel` (owner action; GitHub redirects old URLs); update remote. **done by the owner (repo is github.com/SanTiwari07/NarraReel)**
- [x] P5-02 Full README (10.1).
- [~] P5-03 Demo GIF (≤ 10 MB) + 60-second demo video (made with NarraReel itself!). **24 s demo made with NarraReel itself + GIF (docs/assets); the 60 s narrated-in-cloned-voice video needs the owner's voice**
- [x] P5-04 Dockerfile + `docker run` one-liner. **Built and run on 2026-10-10: `/api/health` ok, UI served, `narrareel make` rendered an 8 s video inside the container. The GPU variant is not built (backlog).**
- [~] P5-05 Hugging Face Space (CPU, Edge/Kokoro voices; cloning shown via Colab link). **docker/Dockerfile.space builds and its demo mode answers on port 7860 (checked 2026-10-10); creating the Space is an owner action**
- [~] P5-06 PyPI release `0.1.0` (trusted publishing via GitHub Actions). **release.yml uses PyPI trusted publishing; configuring it on pypi.org and tagging v0.1.0 are owner actions**
- [x] P5-07 CONTRIBUTING, CODE_OF_CONDUCT, issue/PR templates, 10+ labelled good-first-issues. **Files written. The 10 issues are posted as #1-#10 (drafts in `docs/good-first-issues.md`).**
- [⏸] P5-08 Launch posts (11.2). **owner**

### 7.6 Backlog (Phase 6+)

- Optional AI script helper: "trim to 60 s" / "expand to 6 min" rewrite — bring-your-own API key or local Ollama; never required.
- Background music with automatic ducking under voice (royalty-free sources only).
- Hinglish/Hindi first-class support: Hindi voices, Devanagari fonts, transliteration-aware timing.
- More languages for the UI (i18n) and voices.
- Batch mode: folder of scripts → folder of videos (CLI + UI).
- B-roll/backgrounds: user-supplied clips placed per sentence.
- Auto emoji/keyword highlighting, sound effects on keywords.
- Templates gallery (community presets, shareable JSON).
- VoiceStudio external adapter (if it exposes TTS/clone HTTP).
- CosyVoice / VibeVoice engines.
- Desktop app wrapper (Tauri/Electron) — only if users ask.
- Speaker-consistency checking for cloned voices.
- Multi-voice scripts (dialogue: `[A]: … [B]: …`).

---

## 8. Testing strategy

| Layer | What | Tooling | Runs in CI |
|---|---|---|---|
| Unit | script analysis, duration math, timing estimation/matching, colour conversion, chunking, ASS/SRT writers, presets schema | pytest | always |
| Integration (ffmpeg) | decode/encode, loudnorm, render, preview frame | pytest `-m ffmpeg` | yes (ffmpeg installed in CI) |
| Integration (network) | Edge synthesis | `-m network` | nightly / manual (avoid hammering the service) |
| Integration (models) | Kokoro, faster-whisper, Chatterbox | `-m models` | manual / self-hosted (large downloads) |
| Golden files | `.ass` output per preset, `.srt` output | compare to `tests/golden/` | always |
| Visual | frame perceptual hash per preset | ffmpeg + Pillow | always (small fixtures) |
| API | FastAPI TestClient for every route | pytest | always (Phase 3) |
| Frontend | type-check + a few component tests (Vitest) + one Playwright smoke test (script → export with a mocked API) | Vitest, Playwright | Phase 3 |
| Manual | listening tests for voices/energy; caption sync by eye | checklist in PR template | per release |

Fixtures: short scripts (English, Hindi, numbers, abbreviations), tiny WAVs (< 100 KB), fake Edge boundary streams.

---

## 9. Packaging, install, Docker, Colab, Hugging Face Space

### 9.1 Install paths (what the README will show)

```bash
# Basic (online voices, captions, video)
pip install narrareel
narrareel serve --open

# + offline voice
pip install "narrareel[offline]"

# + precise timing for any voice
pip install "narrareel[align]"

# + clone your voice (GPU recommended; consider a separate venv)
pip install "narrareel[clone]"
```

Requirement: ffmpeg with libass. `narrareel doctor` explains how to install it per OS (winget/choco/scoop on Windows, Homebrew on macOS, apt/dnf on Linux). ⚠️ VERIFY whether the `imageio-ffmpeg` bundled binary includes libass; if yes, we can offer it as an automatic fallback.

### 9.2 Docker (Phase 5)

- `docker run -p 8765:8765 -v narrareel-data:/data ghcr.io/santiwari07/narrareel` → open `http://localhost:8765`.
- Image: Python slim + ffmpeg (with libass) + core + `[offline,align,server]`; licence texts for bundled GPL components (6.2 rule 9).
- GPU image variant with CUDA + `[clone]`.

### 9.3 Colab (Phase 4) — see 5.8.5.

### 9.4 Hugging Face Space (Phase 5)

- Free CPU Space running the same server + UI with Edge and Kokoro voices so people can try NarraReel without installing anything.
- Cloning not enabled on the free Space (CPU + privacy) → link to Colab.
- Rate-limit/size-limit scripts on the Space (e.g. max 2 minutes).
- ⚠️ VERIFY HF Spaces current free-tier limits and Docker SDK support at Phase 5.

---

## 10. Documentation and community

### 10.1 README structure (Phase 5)

1. Logo + name + tagline + badges (CI, licence, PyPI, Python versions, Colab, HF Space).
2. **Demo GIF** at the very top (script → wizard → finished Reel).
3. "Why NarraReel" — 3 bullets (your voice + energy, exact duration, viral captions) + "100% open source & local".
4. Quick start (3 commands) + Docker one-liner + "Try online" link.
5. Features with small screenshots/GIFs per step.
6. Caption preset gallery (thumbnails).
7. Voice cloning section + responsible use + Colab.
8. CLI examples.
9. Comparison table (honest) vs. other tools.
10. Roadmap (link to this file's phases).
11. Contributing (good-first-issues link), licence, credits (Kokoro, Chatterbox, edge-tts, faster-whisper, ffmpeg/libass, Google Fonts).

### 10.2 CONTRIBUTING.md

- Dev setup (Python + Node), running tests, code style (ruff), commit style (conventional commits), how to add: a font, a caption preset, a format, a voice engine (step-by-step with the engine interface).

### 10.3 Good-first-issue ideas (create at launch)

- Add a caption style preset (one JSON file + thumbnail).
- Add a font family (fetch script entry + manifest).
- Add Kokoro voice display names for language X.
- Translate the calibration paragraph to language Y.
- Add a format preset (e.g. LinkedIn 1:1 / X 16:9).
- Improve sentence splitting for language Z.
- Write a docs page for installing ffmpeg on distro W.

---

## 11. Launch and star-growth plan

### 11.1 Before launch (must-haves)
- Demo GIF + a 60-second demo video narrated with a cloned voice (made by NarraReel itself — that's the story).
- Install works in 3 commands on Windows/macOS/Linux; Docker one-liner; HF Space live.
- README polished; 10+ good-first-issues; issue templates.
- A short "before vs after" audio clip: flat AI voice vs NarraReel cloned voice at Hype energy.

### 11.2 Launch channels (spread over ~2 weeks)
1. **Show HN**: "Show HN: NarraReel – turn scripts into Reels in your own cloned voice (open source)".
2. **Reddit**: r/SideProject, r/opensource, r/selfhosted (local-first angle), r/LocalLLaMA (local voice cloning angle), r/NewTubers / r/youtubers (creator angle — follow each sub's self-promo rules ⚠️).
3. **Product Hunt** launch (prepare gallery images + maker comment).
4. **X/Twitter + LinkedIn**: a thread showing the duration feature and caption presets with short clips.
5. **Dev.to / Hashnode article**: "How I built a local voice-cloning Reel generator with Chatterbox, Kokoro and ffmpeg".
6. **Indian creator/dev communities** (Hindi support is a differentiator once ready).
7. Submit to awesome-lists (awesome-tts, awesome-video, awesome-selfhosted ⚠️ check each list's criteria).
8. Post demo Reels/Shorts made with NarraReel, with the repo link in bio/description — the product markets itself.

### 11.3 After launch
- Respond to every issue within 24 h for the first month.
- Weekly small releases with a changelog (shows activity → more stars).
- Thank contributors publicly; add a contributors section.
- Second wave when cloning or Hindi support lands ("NarraReel now speaks Hindi in your voice").

---

## 12. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Edge-TTS service changes/blocks (unofficial) | Default online voices break | Kokoro offline engine; clear error with "switch to offline"; pin edge-tts and watch its repo |
| GPL deps in `[offline]` (phonemizer/espeak-ng) | Licence confusion | Keep optional; document in `THIRD_PARTY_LICENSES.md`; investigate permissive G2P alternative |
| Chatterbox heavy deps / torch pins conflict | Install pain, Windows issues | Separate venv recommendation, Docker GPU image, Colab notebook, Nano model for CPU |
| Python 3.13 compatibility of ML deps | Owner's venv can't install something | Test matrix; document a 3.12 fallback venv if needed |
| ffmpeg missing or without libass | Renderer fails | `narrareel doctor`, clear OS-specific instructions, maybe imageio-ffmpeg fallback |
| Windows path escaping in ffmpeg filters | Render fails on Windows | Always relative paths with `cwd=job_dir`; Windows in CI |
| Transparent WebM alpha not preserved / not supported by an editor | Overlay export broken | Test early (P2-08); offer MOV ProRes 4444 |
| Caption font family name mismatch → libass falls back silently | Wrong font in video | Read family from font file; job-local `fontsdir`; visual tests |
| Timing drift for non-native engines | Captions out of sync | Sentence-anchored estimation + optional whisper alignment |
| Voice cloning misuse | Reputation/ethics | Consent, watermark, responsible-use docs, no "clone from URL" |
| Model download size/bandwidth | Bad first-run experience | Show sizes, consent, int8 models, resume |
| Long scripts (10+ min) memory/time | Slow/crash | Per-sentence processing, caching, progress, cancel |
| Star goal depends on marketing, not code | Goal missed | Section 11 plan; demo-first; ship polished small rather than big and rough |
| Scope creep | Never launches | Phases with clear "done when"; backlog for everything else |

---

## 13. Decision log and open questions

### 13.1 Decisions (2026-10-10)

| # | Decision | Reason |
|---|---|---|
| D1 | Name **NarraReel**, package `narrareel` | Unique on GitHub and PyPI; "narrate + reel" |
| D2 | Licence **MIT** | Maximum adoption; matches most of the ecosystem |
| D3 | Script-first, user writes script (no AI content generation in core) | Differentiates from MoneyPrinterTurbo; matches owner's use case |
| D4 | Core Python library + FastAPI + **React** UI (Streamlit dropped) | Owner wants a best-in-class UI; React gives full design control; core stays UI-agnostic |
| D5 | Basic React styling now; owner will send a design `.md` later | Get the flow right first; theme tokens make restyling easy |
| D6 | Per-sentence synthesis everywhere | Exact timings, duration control via pauses, caching, robustness on long scripts |
| D7 | Edge-TTS kept as online engine (core); Kokoro via `kokoro-onnx` as offline engine (optional extra) | Edge = quality + word timings; Kokoro = offline, but GPL transitive deps and model download |
| D8 | `kokoro-onnx` over official `kokoro` | Official package requires Python < 3.13 and PyTorch; owner's venv is 3.13 |
| D9 | Chatterbox (MIT code + weights) as the cloning engine | Energy (`exaggeration`) control, CPU-capable Nano, watermark, commercial-friendly |
| D10 | VoiceStudio only as optional external service | AGPL-3.0 |
| D11 | Captions via ASS + ffmpeg/libass, MoviePy removed | One-pass fast rendering, rich styling, standard output files |
| D12 | Bundle OFL/Apache Google Fonts + allow user uploads | Consistent cross-platform looks; legal to ship |
| D13 | Duration targeting: pauses first, then speed; always offer "edit script" with word delta | Pauses sound natural; honest guidance |
| D14 | Default loudness −14 LUFS (configurable) | Common social/streaming target ⚠️ VERIFY |
| D15 | 30 fps default | Smoother caption animation |

### 13.2 Open questions

1. Copyright holder line: "SanTiwari07 and NarraReel contributors" or the owner's full name?
2. Hindi/Hinglish: Phase 2 (fonts + Edge Hindi voices) or later?
3. Default voice for first-time users: Edge (better quality, online) or Kokoro (offline, needs download)? Current plan: Edge default, Kokoro suggested.
4. Background music in scope before launch?
5. Do we support Python 3.10 or start at 3.11? (Plan: 3.10+ unless a dependency forces otherwise.)
6. Logo/brand: who designs it? Needed before Phase 5.
7. Permissive alternative to GPL phonemizer for Kokoro — worth investigating?
8. Should "Hype" energy for AI voices be hidden until cloning ships, to avoid disappointing users? (Plan: show it with "Subtle" label.)

---

## 14. Glossary

- **TTS** — text-to-speech.
- **Voice cloning (zero-shot)** — making a TTS model speak in a voice given only a short reference recording, without training.
- **Model weights** — the trained files of an AI model; they have their own licence separate from the code.
- **Engine** — a NarraReel plugin that turns text into speech (Edge, Kokoro, Chatterbox…).
- **Word boundary / word timing** — start and end time of each spoken word.
- **Forced alignment** — finding word timings by matching known text to audio (we use faster-whisper).
- **cps** — characters per second; our speaking-rate unit.
- **Pause scale** — multiplier on default pauses between sentences.
- **Closed loop** — measuring the real result and correcting it to hit the target.
- **ASS** — Advanced SubStation Alpha subtitle format; supports styling and animation.
- **libass** — the library ffmpeg uses to draw ASS subtitles.
- **SRT** — simple subtitle format supported everywhere.
- **LUFS** — loudness unit; platforms normalise audio to roughly −14 LUFS.
- **atempo** — ffmpeg filter that changes speed without changing pitch.
- **OFL** — SIL Open Font License; lets us bundle fonts.
- **LGPL / GPL / AGPL** — copyleft licences of increasing strength (Section 6).
- **SSE** — Server-Sent Events; one-way live updates from server to browser (job progress).
- **Safe zone** — area of a vertical video not covered by platform buttons/text.
- **Perth watermark** — Resemble AI's inaudible watermark in Chatterbox output.

---

## 15. Appendix

### 15.1 References (checked 2026-10-10; stars approximate)

| Project | Stars | Licence | Link |
|---|---|---|---|
| edge-tts | ~12.2k | LGPL-3.0 | https://github.com/rany2/edge-tts |
| Kokoro (official) | ~9.2k | Apache-2.0 | https://github.com/hexgrad/kokoro |
| Kokoro-82M weights | — | Apache-2.0 | https://huggingface.co/hexgrad/Kokoro-82M |
| kokoro-onnx | ~2.8k | MIT | https://github.com/thewh1teagle/kokoro-onnx |
| phonemizer | — | GPL-3.0 | https://github.com/bootphon/phonemizer |
| espeak-ng | — | GPL-3.0 | https://github.com/espeak-ng/espeak-ng |
| Chatterbox | ~26.8k | MIT (code + weights) | https://github.com/resemble-ai/chatterbox |
| faster-whisper | ~25.8k | MIT | https://github.com/SYSTRAN/faster-whisper |
| whisperX | ~24.5k | BSD-2-Clause | https://github.com/m-bain/whisperX |
| CosyVoice | ~23.9k | Apache-2.0 | https://github.com/QwenAudio/CosyVoice |
| VibeVoice | ~54.7k | MIT | https://github.com/microsoft/VibeVoice |
| OmniVoice | ~14.4k | Apache-2.0 (weights undeclared) | https://github.com/k2-fsa/OmniVoice |
| VoiceStudio | ~56.7k | AGPL-3.0 | https://github.com/debpalash/VoiceStudio |
| MoneyPrinterTurbo | ~129k | MIT | https://github.com/harry0703/MoneyPrinterTurbo |
| ShortGPT | ~8k | MIT | https://github.com/RayVentura/ShortGPT |
| captacity | ~139 | MIT | https://github.com/unconv/captacity |
| F5-TTS | ~15.4k | MIT code / CC-BY-NC weights | https://github.com/SWivid/F5-TTS |
| Coqui TTS / XTTS-v2 | ~46k | MPL-2.0 / CPML weights | https://github.com/coqui-ai/TTS |

### 15.2 ffmpeg cookbook (Phase 1–2)

```bash
# Decode any audio to 48 kHz mono float32 raw (for numpy)
ffmpeg -v error -i in.mp3 -ac 1 -ar 48000 -f f32le -

# Probe duration
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 file.wav

# Speed change without pitch change (chain for big factors)
ffmpeg -i in.wav -filter:a "atempo=1.25" out.wav

# Two-pass loudness normalisation (pass 1 measures, pass 2 applies measured values)
ffmpeg -i in.wav -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null -
ffmpeg -i in.wav -af loudnorm=I=-14:TP=-1:LRA=11:measured_I=...:measured_TP=...:measured_LRA=...:measured_thresh=...:offset=...:linear=true out.wav

# "Energy" chain example (tune by ear)
ffmpeg -i in.wav -af "highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=60,equalizer=f=4000:t=q:w=1.2:g=2" out.wav

# Check libass
ffmpeg -hide_banner -filters | grep -E " (ass|subtitles) "
```

### 15.3 Calibration paragraph (English, `assets/calibration/en.txt`)

> "Every great video starts with a simple idea. You write it down, you shape it, and then you share it with the world. Today we're going to turn a plain script into something people actually want to watch, with a clear voice, good timing, and captions that keep their eyes on the screen."

(~55 words, mixed sentence lengths, common sounds. Hindi version to be written.)

### 15.4 Example `project.narrareel.json`

```json
{
  "narrareel_version": "0.2.0",
  "script": "Wake up early. Grind hard. Success is waiting...",
  "duration": { "target_seconds": 30, "option": "adjust_delivery", "speed": 0.95, "pause_scale": 1.6 },
  "voice": { "engine": "edge", "voice_id": "en-US-AndrewNeural", "speed": 0.95, "energy": 0.7 },
  "format": "reels",
  "captions": { "preset": "bold-pop", "overrides": { "colors": { "highlight": "#FF4B4B" } }, "font": "montserrat-black" },
  "background": { "type": "solid", "color": "#101010" },
  "export": { "video": "mp4", "fps": 30, "loudness_lufs": -14 }
}
```

---

## 16. Progress log (2026-10-10)

**Built:** Phases 1-4 in code, Phase 5 files. 272 backend tests pass locally (`pytest -m "not network and not models"`), 13 frontend tests pass, ruff is clean.

**Verified for real (not only by tests):**
- Edge word boundaries are 100-ns ticks; Edge synthesis, 45 s and 20 s targets land within 0.01 s.
- Kokoro offline: model URLs, sizes and SHA-256 pinned from the kokoro-onnx v1.1 release (int8 114 MB + voices 28 MB); `speak` works fully offline.
- faster-whisper alignment works (base model).
- Transparent WebM (VP9) and ProRes 4444 keep alpha through libass (decoded and measured).
- Benchmarks (12-core laptop, libx264 medium): 60 s Reel renders in ~10 s; 8-minute video in ~74 s.
- Wheel builds, ships the web app, fonts and presets; a clean-venv `pip install "<wheel>[server]"` passes `narrareel doctor` and serves UI + API.
- Chatterbox 0.1.7 API read from source: `ChatterboxTTS`, `ChatterboxTurboTTS`, `ChatterboxMultilingualTTS`; there is **no Nano model** in 0.1.7. It installs on Windows + Python 3.13 (torch 2.6.0 resolves, CPU build). A real end-to-end run (clone -> speak) was started but not confirmed when this log was written.

**Not verified (owner / next session):** the release workflow run on GitHub (needs the PyPI setup and a tag); the Colab notebook on Colab itself; transparent overlay inside CapCut/Premiere/DaVinci; Apple-Silicon MPS; creating the Hugging Face Space; PyPI trusted-publishing setup; the 60-second demo video in the owner's own voice; launch posts. (CI, Docker and real Chatterbox cloning were verified later the same day, see the last session update.)

**Decisions added**

| # | Decision | Reason |
|---|---|---|
| D16 | Sentence cache is global (`~/.narrareel/cache/sentences`), keyed by engine, voice, speed, energy and text | Re-targeting or restyling never re-synthesizes |
| D17 | Planner re-plans once with the measured speaking rate when the estimate misses by >3% | Uncalibrated voices still hit the target without a large tempo change |
| D18 | Fonts are instanced to static files at fetch time | libass cannot choose weights from variable fonts |
| D19 | Box highlight uses a thick `\3c` border, not drawn shapes, with a wider word gap | Works in every libass build, no measuring of word positions |
| D20 | Server background files must be uploaded through the API | An open API must not read arbitrary server paths |
| D21 | `narrareel serve --demo`: 350-word cap, no uploads/cloning/model downloads, no token required | Public demo Space |
| D22 | Served URLs use 127.0.0.1, not localhost | `localhost` adds ~2 s per request on this Windows machine (IPv6 fallback) |
| D23 | Legacy Streamlit prototype removed; MoviePy bridge (P1-15) never built | The new renderer shipped first |
| D24 | UI styled from `docs/design.md` tokens (black canvas, electric yellow, Inter); no third-party name or logo used | Owner's design brief |
| D25 | Caption text is measured with Pillow's BASIC layout engine, never Raqm | Raqm is optional in Pillow builds and its kerning moves widths 1-4 %, which changed line breaks (and golden files) between machines |
| D26 | The `clone` extra pins `setuptools<81` | `resemble-perth` (a Chatterbox dependency) imports `pkg_resources`; without it the watermarker is `None` and the model fails to load |
| D27 | Chatterbox Turbo is called with `norm_loudness=False`; the sentence-cache key includes the model variant and a hash of the recording | Turbo's loudness step turns the reference into float64 under NumPy 2 and crashes; the old key served stale audio after a model switch or a deleted-and-recloned voice |
| D28 | Caption placement is a 3 x 4 grid (`layout.align_x` left/centre/right x `layout.position`) plus `offset_x` / `offset_y` in video pixels. Left uses the format's side margin, right also clears the platform button column (`safe_zone.right`); chunks are budgeted for the room that leaves | One tap to put captions where the user wants, with fine nudging; centred output is byte-identical to before, so existing golden files are unchanged |
| D29 | The web app is sized in `rem`; the root font size is 16 px up to a 1600 x 900 window and then grows with the window (about 17 px on 1080p, 19 px on 2K, 24 px on 4K, capped at 26 px, limited by height as well so ultrawide screens do not blow up). The page width is `clamp(80rem, 72vw, 150rem)` | One value scales the whole interface for laptops, 2K and 4K without per-component rules; phones and tablets keep 16 px and use breakpoints, safe-area insets and 44 px touch targets |
| D30 | The UI flow is four steps (Script, Voice, Captions, Make video). Length moved into the Script step as "How long should it be?". Every step uses one centred workspace: controls on the left, a sticky preview + "your video so far" list on the right (`--workspace: 74rem`, `--rail: 20rem`, replacing the `--container` width from D29), and a sticky bottom bar whose right-hand yellow button is always the next action (on the last step: make, stop, then download). Optional settings sit in collapsed rows that show their current value; copy avoids engine names and jargon | Owner feedback (2026-10-11): text was cut off, everything hugged the left, and the flow was too complex for non-technical users. One forward button in one place, plain questions as headings and folded-away detail make the path obvious |
| D31 | (a) When `pkg_resources` is missing, the Chatterbox engine puts a one-function stand-in (`resource_filename`) in `sys.modules` before importing the model, and reports a failed watermarker plainly; the watermark stays on. (b) The voice-model folder is the person's choice: `narrareel/model_store.py` points the Hugging Face hub cache at it (`NARRAREEL_MODEL_DIR`, else the folder chosen in the app and saved in `~/.narrareel/storage.json`, else the hub default), moves our Chatterbox repos there in a background task (copy, then delete; old copies a running model still holds are reported), and the app opens the system folder window on the computer running NarraReel, with a typed path as fallback | (a) On 2026-10-11 a later install upgraded setuptools to 84 despite the D26 pin, and cloning failed with "'NoneType' object is not callable". (b) The models are 6.7 GB (original + Turbo), and the owner's C: drive had 10 GB free |

**Session update (Linux sandbox, same day):** ran the CI commands locally on Linux / Python 3.13: `ruff check` clean, 275 backend tests pass, `check_licenses.py` passes, frontend typecheck + 13 tests + build pass. This found one real cross-platform bug (D25: the `bold-pop` golden file failed on Linux because of the Raqm layout engine) which would have failed the first Linux CI run; fixed. Added the perceptual-hash visual regression (P2-13). The Docker image could not be built in this sandbox (the container cannot reach `deb.debian.org`); Colab notebook commands were checked against the real CLI (flags and voice-id slug match) but not run on Colab.

| D32 | One question per screen. A start screen asks first: start a new video, continue the draft in this tab, or open a saved project; Save project appears only next to a finished video. Length is its own step again (five steps: Script, Length, Voice, Captions, Make video). Voice asks AI voice or my own voice first, then shows that list, then a separate "How should it sound?" screen. My own voice is a wizard: one-time setup (model folder, then install), pick a saved voice or record a new one in three stages (read aloud, listen back, name it); importing and exporting voice files left the app, and uploading a recording only appears when the browser cannot record. Question screens use one centred 48rem column (`--solo`); Captions and Make video keep the preview rail. The draft lives in `sessionStorage` (old `localStorage` drafts are deleted). The window scrollbar is hidden, the script box grows with the text, and the page fills the window so short screens do not scroll. Voice play buttons are yellow | Owner feedback (2026-10-11): too many questions at once, unclear what to click next, content hugging the left, a 10-hour-old script still loaded, Save/Open shown before anything was made, and confusing My voice options (import a voice file next to a guided recording) |
**Session update (Windows, later the same day):** checked the remaining items for real.
- GitHub CI is green on the full matrix (Windows and Ubuntu x Python 3.10, 3.12, 3.13, plus frontend and licences), so the D25 fix and the golden/visual tests transfer across machines.
- Docker: `docker/Dockerfile` and `docker/Dockerfile.space` both build; the app container serves the UI and API and rendered an 8 s video; the Space image answers in demo mode.
- Real voice cloning (Chatterbox 0.1.7, Windows, Python 3.13, CPU) found three bugs that the stand-in tests could not: (1) the model did not load because newer setuptools has no `pkg_resources` (D26); (2) Turbo crashed with "expected Double but found Float" (D27); (3) the sentence cache ignored the model variant and the recording (D27). All three are fixed with tests. After the fixes: clone from a 16 s recording, speak, and `make` with aligned word timings gave a 12.000 s Reel with synced captions.
- Energy measured on CPU: the original model raises pitch (148 to 168 Hz), widens the pitch range and speeds delivery about 11 % between energy 0 and 1; Turbo shows no change. The docs now tell CPU users to set `NARRAREEL_CLONE_MODEL=original` for energy control. The "sounds clearly more energetic" acceptance in section 7.4 is therefore met for the original model only; the owner should still judge it by ear with their own voice.
- 277 backend tests pass, `ruff check narrareel tests scripts` is clean.

**Session update (placement and responsive UI):** added the caption placement pad and the left/right offsets (D28, tests in `test_captions.py`); made the web app responsive from 320 px phones to 4K and ultrawide screens (D29). Checked by emulating 320, 390, 768, 1024, 1440, 1920, 2560, 3440 x 1440 and 3840 px wide windows and a landscape phone: no horizontal page overflow on any of the five steps, and the sticky bar and preview un-stick on short landscape screens. 279 backend tests, 17 frontend tests and `ruff check` pass. Not tested on physical devices or in Safari/Firefox.

**Session update (simpler flow, D30):** redesigned the web app for non-technical users: four steps instead of five, centred two-column workspace with the preview on every step, a sticky Back / Next bar, plain-language copy, one segmented control for energy and voice type, voice tiles with a play button, collapsed caption settings, and the make / stop / download action in the bottom bar. Fixed clipped text in dropdowns (fixed 40 px height) and in caption style thumbnails (1.8x zoom cut the ends off wide styles). Checked at 375, 800 and 1366 px wide: no clipped text, no horizontal overflow, the sticky preview clears the bottom bar; made a real 15 s video end to end. 17 frontend tests, `tsc` and `vite build` pass. Not checked on physical devices or in Safari/Firefox.

**Session update (cloning fix and model folder, D31):** cloning failed because setuptools 84 had replaced the pinned version; fixed in code (D31a) and checked against the real Turbo weights: the model loads with the Perth watermarker and the saved voice speaks (3.2 s clip; the server's voice preview returned audio in 69 s on CPU). Added the "Where should the voice model be kept?" card to My own voice (D31b) with API routes `GET/PUT /api/storage/models`, `POST /api/storage/models/browse` and `/keep`, blocked in demo mode. The move is covered by unit tests on a fake cache; it was not run against the owner's real 6.7 GB copy, and the system folder window was not opened in testing. `test_voice_preview_unavailable_engine` now hides the `chatterbox` package, because it is installed on the owner's machine.

*End of plan document. Next actions: owner items above, then Phase 6 backlog.*
**Session update (one question per screen, D32):** reworked the web app flow from owner feedback; see D32. Checked in the browser at 1600 x 900 and 375 x 812: start screen, script, length (with and without a target), voice source, AI voices, saved voice pick, record stage, captions and make video; no sideways overflow, short screens do not scroll. Recording, the listen-back and name stages, and Save project after a real render were not exercised in the browser. 21 frontend tests, `tsc` and `vite build` pass; the built UI was copied into `narrareel/server/static`.

