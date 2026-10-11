import importlib.machinery
import io
import sys
import types
import zipfile

import numpy as np
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from narrareel import voices
from narrareel.audio import ffmpeg as ff
from narrareel.audio import process as ap
from narrareel.cli import app as cli_app
from narrareel.engines import chatterbox as cb
from narrareel.engines import registry
from narrareel.errors import EngineError, ScriptError
from narrareel.jobs.runner import JobRunner
from narrareel.models import VoiceSelection
from narrareel.server import create_app

SR = ap.SAMPLE_RATE
needs_ffmpeg = pytest.mark.skipif(not ff.available(), reason="ffmpeg not installed")


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))
    registry.reset_instances()


def speechish(seconds=14.0, level=0.2, noise=0.0005, gap_every=0.0, seed=0):
    """Voice-like test signal: a 150 Hz tone gated at a syllable rhythm."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    gate = (np.sin(2 * np.pi * 3.5 * t) > -0.3).astype(float)
    if gap_every:
        gate *= ((t % gap_every) < gap_every * 0.4).astype(float)
    tone = np.sin(2 * np.pi * 150 * t) + 0.5 * np.sin(2 * np.pi * 300 * t)
    return (level * gate * tone + rng.normal(0, noise, t.size)).astype(np.float32)


def wav_bytes(samples):
    buf = io.BytesIO()
    import wave

    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def status_of(report, check_id):
    return next(c.status for c in report.checks if c.id == check_id)


# ------------------------------------------------------------------ quality


@needs_ffmpeg
def test_good_recording_passes_all_checks():
    r = voices.check_reference(speechish())
    assert r.usable and all(c.status == "ok" for c in r.checks), [c for c in r.checks if c.status != "ok"]


def test_too_short_fails():
    r = voices.check_reference(speechish(4.0))
    assert not r.usable and status_of(r, "duration") == "fail"
    assert "at least 8" in next(c.detail for c in r.checks if c.id == "duration")


def test_long_recording_warns_but_is_usable():
    r = voices.check_reference(speechish(70.0))
    assert r.usable and status_of(r, "duration") == "warn"


def test_clipping_is_detected():
    x = np.clip(speechish(level=1.6), -1, 1)
    r = voices.check_reference(x)
    assert status_of(r, "clipping") in ("warn", "fail")
    assert "microphone" in next(c.detail for c in r.checks if c.id == "clipping")


def test_quiet_recording_fails():
    r = voices.check_reference(speechish(level=0.002, noise=0.00001))
    assert status_of(r, "level") == "fail" and not r.usable


def test_noisy_room_warns():
    r = voices.check_reference(speechish(noise=0.02))
    assert status_of(r, "noise") == "warn"
    assert r.usable


def test_mostly_silence_warns_about_speech_ratio():
    r = voices.check_reference(speechish(14.0, gap_every=6.0))
    assert status_of(r, "speech") == "warn"


# ---------------------------------------------------------------- profiles


@needs_ffmpeg
def test_create_profile_end_to_end():
    profile, report = voices.create_profile(wav_bytes(speechish()), "My energetic voice", True, "en")
    assert profile.id == "my-energetic-voice" and profile.consent.accepted
    assert profile.consent.text == voices.CONSENT_TEXT and profile.consent.at
    folder = voices.profile_dir(profile.id)
    for name in ("profile.json", "reference.wav", "reference.mp3"):
        assert (folder / name).is_file(), name
    ref, sr = ap.read_wav(folder / "reference.wav")
    assert sr == voices.REFERENCE_SR and 8 < ref.size / sr <= 30.5
    assert ap.integrated_loudness(ap.resample(ref, sr, SR)) == pytest.approx(-20.0, abs=2.5)
    assert report.usable
    assert voices.get_profile(profile.id).name == "My energetic voice"
    assert [p.id for p in voices.list_profiles()] == [profile.id]


@needs_ffmpeg
def test_profile_ids_are_unique_and_slugged():
    a, _ = voices.create_profile(wav_bytes(speechish()), "Same Name!", True)
    b, _ = voices.create_profile(wav_bytes(speechish(seed=1)), "Same Name!", True)
    assert (a.id, b.id) == ("same-name", "same-name-2")


def test_consent_and_name_are_required():
    data = b"\x00" * 100
    with pytest.raises(ScriptError, match="Confirm that the voice is yours"):
        voices.create_profile(data, "x", False)
    with pytest.raises(ScriptError, match="name"):
        voices.create_profile(data, "  ", True)
    assert voices.list_profiles() == []


@needs_ffmpeg
def test_unusable_recording_is_refused_and_nothing_is_saved():
    with pytest.raises(ScriptError, match="can't be used"):
        voices.create_profile(wav_bytes(speechish(3.0)), "short", True)
    assert voices.list_profiles() == []


@needs_ffmpeg
def test_garbage_upload_is_a_friendly_error():
    with pytest.raises(ScriptError, match="could not be read as audio"):
        voices.decode_recording(b"this is not audio at all" * 50)
    with pytest.raises(ScriptError, match="empty"):
        voices.decode_recording(b"")


@needs_ffmpeg
def test_long_recordings_keep_the_cleanest_30_seconds():
    x = np.concatenate([speechish(20.0, level=1.8), speechish(45.0, level=0.2, seed=3)])
    x = np.clip(x, -1, 1)
    ref = voices.preprocess_reference(x)
    assert ref.size / voices.REFERENCE_SR <= 30.5
    assert np.mean(np.abs(ref) >= 0.944) < 0.001  # the distorted part was not chosen


@needs_ffmpeg
def test_export_import_roundtrip_and_validation():
    p, _ = voices.create_profile(wav_bytes(speechish()), "Portable", True)
    blob = voices.export_profile(p.id)
    voices.delete_profile(p.id)
    assert voices.list_profiles() == []
    back = voices.import_profile(blob)
    assert back.id == "portable" and back.consent.accepted
    again = voices.import_profile(blob)
    assert again.id == "portable-2"

    with pytest.raises(voices.VoiceProfileError, match="not a NarraReel voice"):
        voices.import_profile(b"nope")
    evil = io.BytesIO()
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("profile.json", "{}")
        zf.writestr("reference.wav", b"x")
        zf.writestr("../escape.txt", b"x")
    with pytest.raises(voices.VoiceProfileError, match="unexpected files"):
        voices.import_profile(evil.getvalue())
    noconsent = io.BytesIO()
    prof = back.model_copy(update={"consent": back.consent.model_copy(update={"accepted": False})})
    with zipfile.ZipFile(noconsent, "w") as zf:
        zf.writestr("profile.json", prof.model_dump_json())
        zf.writestr("reference.wav", b"x")
    with pytest.raises(voices.VoiceProfileError, match="no recorded consent"):
        voices.import_profile(noconsent.getvalue())


def test_profile_ids_cannot_escape_the_voices_folder():
    for bad in ("../x", "a/b", "..", "A B", ""):
        with pytest.raises(voices.VoiceProfileError):
            voices.profile_dir(bad)
    with pytest.raises(voices.VoiceProfileError, match="no saved voice"):
        voices.get_profile("missing")
    with pytest.raises(voices.VoiceProfileError):
        voices.delete_profile("missing")


# ----------------------------------------------------------------- engine


def test_energy_mapping_matches_spec():
    assert cb.energy_to_params(0.0) == pytest.approx((0.3, 0.6))
    assert cb.energy_to_params(0.5) == pytest.approx((0.6, 0.45))
    assert cb.energy_to_params(1.0) == pytest.approx((0.9, 0.3))
    assert cb.energy_to_params(7) == cb.energy_to_params(1.0)


def test_model_choice(monkeypatch):
    monkeypatch.delenv("NARRAREEL_CLONE_MODEL", raising=False)
    assert cb.pick_model("cuda") == "original"
    assert cb.pick_model("cpu") == "turbo"
    assert cb.pick_model("cuda", "hi") == "multilingual"
    monkeypatch.setenv("NARRAREEL_CLONE_MODEL", "turbo")
    assert cb.pick_model("cuda") == "turbo"
    assert cb.pick_device("cpu") == "cpu"


def test_status_when_not_installed(monkeypatch):
    monkeypatch.setattr(cb.importlib.util, "find_spec", lambda name: None)
    s = cb.ChatterboxEngine().status()
    assert not s.available and 'pip install "narrareel[clone]"' in s.reason


class _Tensor:
    def __init__(self, a):
        self.a = a

    def squeeze(self):
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.a


@pytest.fixture
def fake_chatterbox(monkeypatch):
    calls = []

    class Model:
        sr = 24000

        @classmethod
        def from_pretrained(cls, device):
            m = cls()
            m.device = device
            return m

        def generate(self, text, **kwargs):
            calls.append((text, kwargs))
            return _Tensor(np.sin(np.arange(int(0.5 * self.sr)) / 20).astype("float32"))

    pkg = types.ModuleType("chatterbox")
    pkg.__spec__ = importlib.machinery.ModuleSpec("chatterbox", None)
    pkg.__path__ = []
    for sub, cls in (("tts", "ChatterboxTTS"), ("tts_turbo", "ChatterboxTurboTTS"),
                     ("mtl_tts", "ChatterboxMultilingualTTS")):
        mod = types.ModuleType(f"chatterbox.{sub}")
        setattr(mod, cls, type(cls, (Model,), {}))
        monkeypatch.setitem(sys.modules, f"chatterbox.{sub}", mod)
    monkeypatch.setitem(sys.modules, "chatterbox", pkg)
    monkeypatch.delenv("NARRAREEL_CLONE_MODEL", raising=False)
    monkeypatch.setenv("NARRAREEL_DEVICE", "cuda")
    return calls


@needs_ffmpeg
def test_engine_speaks_with_a_saved_voice(fake_chatterbox):
    profile, _ = voices.create_profile(wav_bytes(speechish()), "Me", True)
    eng = cb.ChatterboxEngine()
    assert eng.status().available and eng.capabilities.cloning
    assert [v.id for v in eng.list_voices()] == ["me"] and eng.list_voices()[0].custom
    out = eng.synthesize("Hello there.", VoiceSelection(engine="chatterbox", voice_id="me", energy=1.0))
    assert out.sample_rate == 24000 and out.samples.size == 12000 and out.words is None
    text, kwargs = fake_chatterbox[0]
    assert text == "Hello there."
    assert kwargs["audio_prompt_path"].endswith("reference.wav")
    assert kwargs["exaggeration"] == pytest.approx(0.9) and kwargs["cfg_weight"] == pytest.approx(0.3)
    assert profile.consent.accepted


@needs_ffmpeg
def test_engine_model_variants_get_the_right_arguments(fake_chatterbox, monkeypatch):
    voices.create_profile(wav_bytes(speechish()), "Me", True, "en")
    voices.create_profile(wav_bytes(speechish(seed=2)), "Hindi", True, "hi")
    eng = cb.ChatterboxEngine()
    sel = lambda v: VoiceSelection(engine="chatterbox", voice_id=v, energy=0.5)  # noqa: E731
    monkeypatch.setenv("NARRAREEL_CLONE_MODEL", "turbo")
    eng.synthesize("a", sel("me"))
    # turbo has no exaggeration, and its own loudness step crashes under NumPy 2, so that is switched off
    assert set(fake_chatterbox[-1][1]) == {"audio_prompt_path", "norm_loudness"}
    assert fake_chatterbox[-1][1]["norm_loudness"] is False
    monkeypatch.delenv("NARRAREEL_CLONE_MODEL")
    eng.synthesize("b", sel("hindi"))
    assert fake_chatterbox[-1][1]["language_id"] == "hi"


@needs_ffmpeg
def test_cached_sentences_do_not_leak_across_recordings_or_models(fake_chatterbox, monkeypatch):
    sel = VoiceSelection(engine="chatterbox", voice_id="me")
    voices.create_profile(wav_bytes(speechish()), "Me", True)
    eng = cb.ChatterboxEngine()
    first = eng.cache_voice_key(sel)
    assert eng.cache_voice_key(sel) == first
    monkeypatch.setenv("NARRAREEL_CLONE_MODEL", "turbo")
    assert eng.cache_voice_key(sel) != first  # another model variant sounds different
    monkeypatch.delenv("NARRAREEL_CLONE_MODEL")
    voices.delete_profile("me")
    voices.create_profile(wav_bytes(speechish(level=0.3)), "Me", True)  # re-cloned: the id is reused
    assert eng.cache_voice_key(sel) != first


@needs_ffmpeg
def test_engine_errors_are_friendly(fake_chatterbox):
    eng = cb.ChatterboxEngine()
    with pytest.raises(voices.VoiceProfileError, match="no saved voice"):
        eng.synthesize("x", VoiceSelection(engine="chatterbox", voice_id="ghost"))
    profile, _ = voices.create_profile(wav_bytes(speechish()), "Me", True)
    voices.reference_path(profile.id).unlink()
    with pytest.raises(EngineError, match="Clone the voice again"):
        eng.synthesize("x", VoiceSelection(engine="chatterbox", voice_id="me"))


@needs_ffmpeg
def test_speak_pipeline_works_with_a_cloned_voice(fake_chatterbox, tmp_path):
    """The engine plugs into the same pipeline: tempo for speed, estimated word timings."""
    from narrareel.jobs.workspace import Workspace
    from narrareel.pipeline.speak import speak

    voices.create_profile(wav_bytes(speechish()), "Me", True)
    ws = Workspace.create(tmp_path / "jobs")
    res = speak("Wake up early. Grind hard.", VoiceSelection(engine="chatterbox", voice_id="me", speed=1.2,
                energy=0.9), ws, timing="estimated", cache=False)
    assert res.duration > 1 and res.words and all(w.source == "estimated" for w in res.words)


# --------------------------------------------------------------------- api


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(runner=JobRunner(tmp_path / "jobs"), static_dir=tmp_path / "no-ui")) as c:
        yield c


@needs_ffmpeg
def test_api_clone_flow(client):
    good = wav_bytes(speechish())
    files = {"file": ("take1.wav", good, "audio/wav")}

    chk = client.post("/api/voices/clone/check", files=files)
    assert chk.status_code == 200 and chk.json()["usable"] is True
    assert {c["id"] for c in chk.json()["checks"]} == {"duration", "clipping", "level", "noise", "speech"}

    no_consent = client.post("/api/voices/clone", files=files, data={"name": "Me", "consent": "false"})
    assert no_consent.status_code == 422 and "Confirm" in no_consent.json()["error"]

    ok = client.post("/api/voices/clone", files=files, data={"name": "Me", "consent": "true", "language": "en"})
    assert ok.status_code == 200, ok.text
    voice_id = ok.json()["profile"]["id"]
    assert ok.json()["quality"]["usable"] and ok.json()["profile"]["consent"]["accepted"]

    listed = client.get("/api/voices/custom").json()
    assert [v["id"] for v in listed] == [voice_id]
    ref = client.get(f"/api/voices/custom/{voice_id}/reference.mp3")
    assert ref.status_code == 200 and ref.headers["content-type"] == "audio/mpeg"

    exported = client.get(f"/api/voices/custom/{voice_id}/export")
    assert exported.status_code == 200 and zipfile.is_zipfile(io.BytesIO(exported.content))
    assert client.delete(f"/api/voices/custom/{voice_id}").json() == {"deleted": True}
    assert client.get("/api/voices/custom").json() == []
    imported = client.post("/api/voices/custom/import", files={"file": ("v.zip", exported.content)})
    assert imported.status_code == 200 and imported.json()["id"] == voice_id

    assert client.delete("/api/voices/custom/nope").status_code == 422
    assert client.delete("/api/voices/custom/..%2Fx").status_code in (404, 422)
    assert client.post("/api/voices/custom/import", files={"file": ("v.zip", b"nope")}).status_code == 422


@needs_ffmpeg
def test_api_clone_rejects_bad_audio_and_guides_the_user(client):
    bad = client.post("/api/voices/clone/check", files={"file": ("x.wav", b"garbage" * 100)})
    assert bad.status_code == 422 and "could not be read as audio" in bad.json()["error"]
    short = client.post("/api/voices/clone", files={"file": ("s.wav", wav_bytes(speechish(3.0)))},
                        data={"name": "Short", "consent": "true"})
    assert short.status_code == 422 and "can't be used" in short.json()["error"]
    guide = client.get("/api/voices/guided-text").json()
    assert {"energetic", "calm", "hindi", "consent"} <= set(guide)
    assert "impersonate" in guide["consent"]


# --------------------------------------------------------------------- cli


@needs_ffmpeg
def test_cli_clone_requires_consent_and_saves(tmp_path):
    runner = CliRunner()
    rec = tmp_path / "me.wav"
    rec.write_bytes(wav_bytes(speechish()))
    refused = runner.invoke(cli_app, ["clone", str(rec), "--name", "Me"], input="n\n")
    assert refused.exit_code == 1 and "confirmation" in refused.output
    assert voices.list_profiles() == []
    ok = runner.invoke(cli_app, ["clone", str(rec), "--name", "Me", "--i-have-consent"])
    assert ok.exit_code == 0, ok.output
    assert "chatterbox:me" in ok.output and "Length" in ok.output
    assert [p.id for p in voices.list_profiles()] == ["me"]
    assert runner.invoke(cli_app, ["clone", "nope.wav", "--name", "x", "--i-have-consent"]).exit_code == 1


def test_perth_gets_pkg_resources_when_setuptools_dropped_it(monkeypatch):
    # setuptools 81+ has no pkg_resources; resemble-perth then sets its watermarker to None (D31)
    monkeypatch.setitem(sys.modules, "pkg_resources", None)  # makes `import pkg_resources` fail
    perth = types.ModuleType("perth")
    perth.PerthImplicitWatermarker = None
    reloaded = []
    monkeypatch.setitem(sys.modules, "perth", perth)
    monkeypatch.setattr(cb.importlib, "reload", lambda m: reloaded.append(m) or m)
    cb._ensure_pkg_resources()
    shim = sys.modules["pkg_resources"]
    assert shim.resource_filename("narrareel", "presets").replace("\\", "/").endswith("narrareel/presets")
    assert reloaded == [perth]  # perth is re-imported so it picks the stand-in up


def test_missing_watermarker_is_reported_plainly(monkeypatch):
    perth = types.ModuleType("perth")
    perth.PerthImplicitWatermarker = None
    monkeypatch.setitem(sys.modules, "perth", perth)
    monkeypatch.setitem(sys.modules, "perth.perth_net.perth_net_implicit.perth_watermarker", None)
    with pytest.raises(cb.WatermarkerMissing, match="resemble-perth.*pip install"):
        cb._check_watermarker()
    perth.PerthImplicitWatermarker = object
    cb._check_watermarker()  # a working watermarker passes
