"""Voice cloning with Chatterbox (WHAT_TO_DO.md 5.3.4). Optional: ``pip install "narrareel[clone]"``.

Code and weights are MIT. Every output carries Resemble AI's Perth watermark; we keep it on.
API checked against chatterbox-tts 0.1.7: ``ChatterboxTTS`` (English, ``exaggeration`` and
``cfg_weight``), ``ChatterboxTurboTTS`` (English, faster, no exaggeration control) and
``ChatterboxMultilingualTTS`` (``language_id``). There is no "Nano" model in 0.1.7.

Not exercised against the real weights in CI: the unit tests drive this class with a stand-in
``chatterbox`` module. See docs/voice-cloning.md for how to run the real check.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.resources
import importlib.util
import logging
import os
import sys
import threading
import types

import numpy as np

from .. import config, model_store
from ..errors import EngineError, EngineUnavailable
from ..models import EngineCapabilities, EngineStatus, VoiceInfo, VoiceSelection
from ..voices import get_profile, list_profiles, reference_path
from .base import ProgressFn, SentenceAudio, TTSEngine

log = logging.getLogger("narrareel.engines.chatterbox")

INSTALL_HINT = 'Install with: pip install "narrareel[clone]" (a GPU is recommended)'
MODELS = ("original", "turbo", "multilingual")


def energy_to_params(energy: float) -> tuple[float, float]:
    """(exaggeration, cfg_weight) from the 0..1 energy slider (section 5.4)."""
    e = min(1.0, max(0.0, energy))
    return 0.3 + 0.6 * e, 0.6 - 0.3 * e


def pick_device(requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def pick_model(device: str, language: str = "en") -> str:
    env = os.environ.get("NARRAREEL_CLONE_MODEL", "").lower()
    if env in MODELS:
        return env
    if not language.lower().startswith("en"):
        return "multilingual"
    return "original" if device in ("cuda", "mps") else "turbo"


class WatermarkerMissing(Exception):
    """Chatterbox's watermarker (resemble-perth) failed to import, so no model can be built."""


def _ensure_pkg_resources() -> None:
    """Give resemble-perth the one ``pkg_resources`` function it uses, if setuptools no longer has it.

    perth does ``from pkg_resources import resource_filename``. setuptools 81 dropped
    ``pkg_resources``, and when that import fails perth quietly sets its watermarker to ``None``, so
    every model then dies with "'NoneType' object is not callable". The ``setuptools<81`` pin in the
    ``clone`` extra is not enough on its own: any later ``pip install`` (torch, for one) can upgrade
    setuptools again (D26, D31).
    """
    try:
        importlib.import_module("pkg_resources")
        return
    except ImportError:
        pass
    shim = types.ModuleType("pkg_resources")

    def resource_filename(package: str, resource: str) -> str:
        return str(importlib.resources.files(package).joinpath(resource))

    shim.resource_filename = resource_filename  # type: ignore[attr-defined]
    sys.modules["pkg_resources"] = shim
    log.info("pkg_resources is missing (setuptools 81+); using a small stand-in for resemble-perth")
    # an earlier attempt in this process may have imported perth without its watermarker
    perth = sys.modules.get("perth")
    if perth is not None and getattr(perth, "PerthImplicitWatermarker", None) is None:
        importlib.reload(perth)


def _check_watermarker() -> None:
    """Fail with the real reason, not a NoneType error, when perth's watermarker did not import."""
    perth = sys.modules.get("perth")
    if perth is None or getattr(perth, "PerthImplicitWatermarker", True) is not None:
        return
    try:
        importlib.import_module("perth.perth_net.perth_net_implicit.perth_watermarker")
        reason = "unknown reason"
    except Exception as exc:  # the import error perth swallowed
        reason = f"{type(exc).__name__}: {exc}"
    raise WatermarkerMissing(
        f"Chatterbox's audio watermarker (resemble-perth) could not load ({reason}). "
        'Reinstall it with: pip install --force-reinstall resemble-perth "setuptools<81"'
    )


class ChatterboxEngine(TTSEngine):
    id = "chatterbox"
    display_name = "Your voice (Chatterbox)"
    version = "1"
    capabilities = EngineCapabilities(
        offline=True,
        native_word_timing=False,
        native_speed=False,  # synthesize at 1.0 and let the pipeline apply atempo
        energy_control="expressive",
        cloning=True,
        languages=["en", "multi"],
        needs_gpu="recommended",
    )

    def __init__(self) -> None:
        self._models: dict[str, object] = {}
        self._lock = threading.Lock()
        self._device: str | None = None

    # -------------------------------------------------------------- status

    def status(self) -> EngineStatus:
        if importlib.util.find_spec("chatterbox") is None:
            return EngineStatus(available=False, reason=INSTALL_HINT)
        return EngineStatus(available=True)

    # -------------------------------------------------------------- voices

    def list_voices(self, language: str | None = None) -> list[VoiceInfo]:
        voices = [
            VoiceInfo(
                engine="chatterbox", id=p.id, name=p.name, language=p.language, gender="unknown",
                accent=None, offline=True, custom=True,
            )
            for p in list_profiles()
        ]  # fmt: skip
        if language:
            voices = [v for v in voices if v.language.lower().startswith(language.lower())]
        return voices

    # -------------------------------------------------------------- models

    def _device_name(self) -> str:
        if self._device is None:
            self._device = pick_device(config.load_settings().device)
        return self._device

    def _load(self, kind: str):
        with self._lock:
            if kind in self._models:
                return self._models[kind]
            device = self._device_name()
            _ensure_pkg_resources()
            folder = model_store.apply()  # the folder the person chose for the big download
            module_name, class_name = {
                "turbo": ("chatterbox.tts_turbo", "ChatterboxTurboTTS"),
                "multilingual": ("chatterbox.mtl_tts", "ChatterboxMultilingualTTS"),
            }.get(kind, ("chatterbox.tts", "ChatterboxTTS"))
            try:
                module = importlib.import_module(module_name)
                _check_watermarker()
                model = getattr(module, class_name).from_pretrained(device=device)
            except ImportError as exc:
                raise EngineUnavailable(INSTALL_HINT) from exc
            except WatermarkerMissing as exc:
                raise EngineError(str(exc)) from exc
            except Exception as exc:
                raise EngineError(
                    f"The cloning model could not be loaded on {device} ({exc}). The first run downloads "
                    f"about 4 GB into {folder}, so check your connection and the free space there."
                ) from exc
            self._models[kind] = model
            return model

    def prepare(self, progress: ProgressFn | None = None) -> None:
        if progress:
            progress(0.05, "Loading the voice model (the first run downloads about 4 GB)")
        self._load(pick_model(self._device_name()))
        if progress:
            progress(1.0, "Ready")

    # ----------------------------------------------------------- synthesis

    def cache_voice_key(self, voice: VoiceSelection) -> str:
        # The same name can be re-recorded, and the model variant changes the sound: both must miss the cache.
        ref = reference_path(voice.voice_id)
        digest = hashlib.sha256(ref.read_bytes()).hexdigest()[:16] if ref.is_file() else "missing"
        kind = pick_model(self._device_name(), get_profile(voice.voice_id).language)
        return f"{voice.voice_id}:{kind}:{digest}"

    def synthesize(self, text: str, voice: VoiceSelection) -> SentenceAudio:
        profile = get_profile(voice.voice_id)
        ref = reference_path(voice.voice_id)
        if not ref.is_file():
            raise EngineError(f"The recording for '{profile.name}' is missing. Clone the voice again.")
        kind = pick_model(self._device_name(), profile.language)
        model = self._load(kind)
        exaggeration, cfg = energy_to_params(voice.energy)
        try:
            try:
                import torch

                torch.manual_seed(profile.seed)  # same seed for every sentence keeps the voice steady
            except ImportError:  # the real chatterbox always brings torch; stand-ins may not
                pass
            kwargs: dict[str, object] = {"audio_prompt_path": str(ref)}
            if kind == "multilingual":
                kwargs.update(language_id=profile.language.split("-")[0].lower(),
                              exaggeration=exaggeration, cfg_weight=cfg)  # fmt: skip
            elif kind == "original":
                kwargs.update(exaggeration=exaggeration, cfg_weight=cfg)
            else:
                # Turbo's own loudness step turns the reference into float64 under NumPy 2 and then
                # crashes; the reference is already loudness-normalised when the voice is saved.
                kwargs.update(norm_loudness=False)
            with self._lock:
                wav = model.generate(text, **kwargs)  # type: ignore[attr-defined]
            samples = wav.squeeze().detach().cpu().numpy().astype("float32")
        except (EngineError, EngineUnavailable):
            raise
        except Exception as exc:
            raise EngineError(f"Your voice could not speak '{text[:40]}...': {exc}") from exc
        if samples.ndim != 1 or samples.size == 0:
            raise EngineError("The cloning model returned no audio.")
        return SentenceAudio(np.ascontiguousarray(samples), int(model.sr), None)  # type: ignore[attr-defined]
