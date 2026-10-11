# Contributing to NarraReel

Thank you for helping. The easiest first contributions are a caption preset, a font, a format, or a docs fix. None of them needs
you to touch the core.

## Set up

```bash
git clone https://github.com/SanTiwari07/NarraReel.git
cd NarraReel
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -e ".[dev,server]"
ffmpeg -version                                       # needs libass; `narrareel doctor` checks this
pytest -m "not network and not models"                # the same command CI runs
ruff check narrareel tests scripts
```

Web app (needs Node 22):

```bash
cd frontend
npm ci
npm run dev                  # http://127.0.0.1:5173, proxies /api to the server below
# in another terminal:  narrareel serve --dev
npm run typecheck && npm test
npm run build:wheel          # builds the UI into narrareel/server/static (git-ignored)
```

When you change API routes or models, regenerate the TypeScript types:

```bash
python scripts/export_openapi.py && (cd frontend && npm run api:types)
```

## Ground rules

- **Conventional commits** (`feat(captions): ...`, `fix(timing): ...`, `docs: ...`).
- **Tests for behaviour changes.** Pure logic goes in `tests/unit`; use the fake engine in
  `tests/unit/fake_engine.py` so tests need no network or models. Mark tests that need ffmpeg `ffmpeg`, network
  `network`, downloaded models `models`.
- **Licences matter.** Our code is MIT. Core dependencies must be MIT/BSD/Apache/ISC/PSF/MPL/LGPL
  (`python scripts/check_licenses.py`). Fonts must be OFL or Apache-2.0, models must allow commercial use, and
  nothing AGPL is imported. Update `THIRD_PARTY_LICENSES.md` when dependencies change.
- **The core never imports the server, CLI or UI.** Heavy or copyleft dependencies are imported lazily inside
  the engine that needs them.
- Error messages say what happened **and** what to do.

## Add a caption preset

1. Add an entry to `PRESETS` in `scripts/write_presets.py` (or copy a JSON file in `narrareel/presets/styles/`).
2. `python scripts/write_presets.py` validates it and rewrites the JSON files and `schema.json`.
3. `UPDATE_GOLDEN=1 pytest tests/unit/test_captions.py` creates the golden `.ass` file; read the diff.
4. `narrareel preview script.txt --style your-preset -o p.png` and look at it. Add it to the gallery if it is good.

## Add a font

1. Add a `Family(...)` to `scripts/fetch_fonts.py` (OFL or Apache-2.0 only; the script refuses anything else and
   instances variable fonts into static ones, which libass needs).
2. `python scripts/fetch_fonts.py` downloads it with its licence and rewrites `manifest.json`.
3. Check it in the Captions step. Keep the bundle under 15 MB.

## Add a format

Copy `narrareel/presets/formats/reels.json`, change the size and the four caption positions (fractions of the
frame height), and run the caption tests.

## Add a voice engine

An engine turns **one sentence** into audio; the pipeline handles pauses, timing, speed and duration targets.

1. Create `narrareel/engines/yourengine.py` with a class that extends `TTSEngine` (`engines/base.py`):
   `status()`, `list_voices()`, `synthesize(text, voice) -> SentenceAudio`, and optionally `prepare()`.
2. Import heavy libraries **inside** methods and report missing extras through `status()` with the pip command.
3. If the engine reports word times, return them in `SentenceAudio.words`; otherwise timings are estimated
   (or aligned when `narrareel[align]` is installed).
4. Register it in `engines/registry.py` and add tests with a stand-in for the library (see
   `tests/unit/test_cloning.py` for the pattern).
5. Check the licence of the code **and** the weights (see section 6.2 of `WHAT_TO_DO.md`).

## Good first issues

Open ones are under the [`good first issue` label](https://github.com/SanTiwari07/NarraReel/labels/good%20first%20issue).
Comment on one to claim it. Ideas that fit well: caption presets, fonts, Kokoro voice names for other languages, calibration paragraphs in other languages,
sentence splitting for your language, ffmpeg install docs for your distro, format presets (LinkedIn, X).

## Reporting bugs

Run `narrareel doctor` and paste its output. For caption sync problems attach `words.json` and `captions.ass`
from the job folder (`~/.narrareel/jobs/<id>/`). Please do not attach voice recordings of other people.
