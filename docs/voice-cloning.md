# Cloning your voice

NarraReel can narrate in **your own voice** with an energy control (calm to hype), using
[Chatterbox](https://github.com/resemble-ai/chatterbox) (MIT code, MIT weights). It is *zero-shot*: there is
no training. A voice is a cleaned 10-30 second recording plus a few settings, so it takes seconds to create
and is a tiny file you can export and share between your own computers.

## Quick start

```bash
pip install "narrareel[clone]"      # the cloning engine (large: PyTorch + the model)
narrareel serve --open              # Voice step -> "My voice" tab: record, check, save
```

Or from the terminal:

```bash
narrareel clone my-recording.wav --name "My voice" --i-have-consent
narrareel make script.txt --voice chatterbox:my-voice --energy 0.8 --target 60s -o reel.mp4
```

You can record and save voices **without** the cloning engine installed. Only speaking with them needs it.

## How to record a good reference

- Read the guided paragraph on screen **the way you want your videos to sound**. The clone copies how you speak
  (pace, energy, warmth), not just how you sound. For an energetic channel, record energetically.
- 15-30 seconds in a quiet room. Speak continuously and keep the microphone at a steady distance.
- NarraReel checks the recording instantly: length, clipping, loudness, background noise and how much of it is
  speech. Items marked *Fix* must be fixed; *Check* items are warnings.
- Longer recordings are trimmed to the cleanest 30 seconds. Browser recordings are captured raw (no noise
  suppression or auto-gain), because the clone would copy those effects.

## Models and hardware

| Your computer | What happens |
|---|---|
| NVIDIA GPU (CUDA) | Original Chatterbox (500M): best quality, fast. |
| Apple Silicon | Original model on MPS (not verified by the maintainers; please report results). |
| CPU only | Chatterbox Turbo (350M): works, but has **no energy control** (see below). Or use the free Colab notebook. |
| Non-English reference | Multilingual model, chosen automatically from the voice's language. |

Override with `NARRAREEL_CLONE_MODEL=original|turbo|multilingual` and `NARRAREEL_DEVICE=cpu|cuda|mps`.

The first run downloads the weights from Hugging Face: about 3 GB for the original model and 4 GB for Turbo.
The app asks where to keep them (My own voice, "Where should the voice model be kept?"), so they do not have to go on a
full system drive; changing the folder later moves what is already downloaded. Outside the app, set
`NARRAREEL_MODEL_DIR` to a folder such as `D:\NarraReel models` (the weights go in its `huggingface` subfolder).
Speed is applied by time-stretching
(the model has no speed control). Energy maps to the model's `exaggeration` and `cfg_weight` on the original and
multilingual models; the Turbo model has no such control, so there energy only changes the audio processing.

Measured on 2026-10-10 on a CPU-only Windows laptop (Python 3.13, `chatterbox-tts` 0.1.7), same sentence and voice,
energy 0.0 versus 1.0:

| Model | Average pitch | Pitch range | Length |
|---|---|---|---|
| Original (`NARRAREEL_CLONE_MODEL=original`) | 148 Hz to 168 Hz | 145 Hz to 158 Hz | 6.1 s to 5.4 s |
| Turbo (the CPU default) | 147 Hz to 148 Hz | 137 Hz to 136 Hz | no change |

So on a CPU, set `NARRAREEL_CLONE_MODEL=original` if you want the Energy slider to change the delivery. It takes about
a minute for a short sentence on CPU; a GPU or the Colab notebook is much faster.

Install notes (checked on 2026-10-10): `chatterbox-tts` 0.1.7 resolves on Python 3.13 and pins `torch==2.6.0`.
Its pins can clash with other packages, so install the `clone` extra in its own virtual environment if you hit
conflicts. The `clone` extra pins `setuptools<81`: Chatterbox's watermarking package imports `pkg_resources`, which
newer setuptools no longer ships, and without it the model fails to load. Another install can still upgrade setuptools
later, so NarraReel also supplies the one function the watermarker needs when `pkg_resources` is missing; the
watermark stays on either way. On Windows the PyPI `torch` wheel is CPU-only; for a GPU follow the PyTorch install selector first.

## Free GPU: Google Colab

Open [`notebooks/NarraReel_Colab.ipynb`](../notebooks/NarraReel_Colab.ipynb) in Colab, choose a GPU runtime,
upload your recording and script, and download the finished video. The notebook uses plain cells, not a
tunnelled web UI.

## Responsible use

- **Only clone a voice you own or have explicit permission to use.** NarraReel asks you to confirm this every
  time, and stores the confirmation (text and time) in the voice's `profile.json`.
- Imported voices must carry that recorded confirmation.
- Chatterbox embeds Resemble AI's **Perth watermark**, an inaudible marker that lets tools detect AI-generated
  speech. NarraReel never disables it.
- There is deliberately no way to clone from a link to someone else's video.
- Many platforms ask you to label AI-generated or synthetic content. Rules change, so check the current policy
  of each platform you publish on before you post.

## Verifying the real model on your machine

The unit tests drive the engine with a stand-in model, so the real weights are not part of CI. To check yours:

```bash
pip install "narrareel[clone]"
narrareel clone my-recording.wav --name "My voice" --i-have-consent
narrareel speak script.txt --voice chatterbox:my-voice --energy 0.9 -o out/
```

Listen to `out/voice.mp3`, then repeat with `--energy 0.2` and compare.
