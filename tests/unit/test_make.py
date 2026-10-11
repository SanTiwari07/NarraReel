import json
import subprocess

import numpy as np
import pytest
from PIL import Image
from typer.testing import CliRunner

from narrareel.audio import ffmpeg as ff
from narrareel.cli import app
from narrareel.errors import FFmpegError, JobCancelled, ScriptError
from narrareel.jobs.workspace import Workspace
from narrareel.pipeline.make import export_name, make_video, preview_frame
from narrareel.project import ProjectConfig
from narrareel.render import ffmpeg_render as fr

from .fake_engine import FakeEngine

pytestmark = [
    pytest.mark.ffmpeg,
    pytest.mark.skipif(not (ff.available() and ff.has_libass()), reason="ffmpeg with libass needed"),
]

SCRIPT = "Wake up early. Grind hard every single day, because success is waiting for you."
runner = CliRunner()


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))


def project(**kw) -> ProjectConfig:
    base = {"script": SCRIPT, "voice": {"engine": "fake", "voice_id": "v1"}}
    base.update(kw)
    return ProjectConfig.model_validate(base)


def probe(path, entries):
    out = subprocess.run(
        [ff.find_ffprobe(), "-v", "error", "-show_entries", entries, "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    return json.loads(out)


def frame_at(video, t, codec=None):
    out = video.with_suffix(f".{int(t * 1000)}.png")
    cmd = [ff.find_ffmpeg(), "-v", "error", "-y"]
    if codec:
        cmd += ["-c:v", codec]
    cmd += ["-ss", str(t), "-i", str(video), "-frames:v", "1", "-pix_fmt", "rgba", str(out)]
    subprocess.run(cmd, check=True)
    return np.array(Image.open(out))


# ---------------------------------------------------------------- project


def test_project_roundtrip_and_defaults(tmp_path):
    p = project()
    path = p.save(tmp_path / "x.narrareel.json")
    again = ProjectConfig.load(path)
    assert again == p and again.format == "reels" and again.export.video == "mp4"


def test_project_transparent_forces_alpha_container():
    p = project(background={"type": "transparent"})
    assert p.export.video == "webm"
    assert project(background={"type": "transparent"}, export={"video": "mov"}).export.video == "mov"


def test_project_load_errors(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ScriptError, match="not a valid NarraReel project"):
        ProjectConfig.load(bad)
    with pytest.raises(ScriptError, match="Could not open"):
        ProjectConfig.load(tmp_path / "missing.json")


def test_export_name():
    assert export_name("Wake up early! Grind hard.", "reels", "mp4") == "narrareel_wake-up-early_reels.mp4"
    assert export_name("???", "youtube", "webm") == "narrareel_video_youtube.webm"
    assert export_name("नमस्ते दुनिया", "reels", "mp4") == "narrareel_नमस्ते-दुनिया_reels.mp4"


# ----------------------------------------------------------------- render


def test_build_command_is_windows_safe_and_relative():
    spec = fr.RenderSpec(1080, 1920, 30, 10.0)
    args = fr.build_command(spec, "out.mp4")
    vf = args[args.index("-vf") + 1]
    assert vf == "subtitles=captions.ass:fontsdir=fonts"
    assert ":\\" not in " ".join(args) and "C:" not in " ".join(args)
    assert args[-1] == "out.mp4" and "-movflags" in args


def test_build_command_transparent_variants():
    spec = fr.RenderSpec(1080, 1920, 30, 10.0, background="transparent", container="webm")
    vf = fr.build_command(spec, "o.webm")
    joined = " ".join(vf)
    assert "alpha=1" in joined and "yuva420p" in joined and "libvpx-vp9" in joined
    mov = " ".join(fr.build_command(
        fr.RenderSpec(1080, 1920, 30, 10.0, background="transparent", container="mov"), "o.mov"))
    assert "prores_ks" in mov and "yuva444p10le" in mov
    with pytest.raises(FFmpegError, match="MP4 cannot hold transparency"):
        fr.build_command(fr.RenderSpec(1080, 1920, 30, 10.0, background="transparent"), "o.mp4")


def test_build_command_image_and_video_backgrounds():
    img = fr.build_command(
        fr.RenderSpec(1080, 1920, 30, 5.0, background="image", background_file="bg.jpg", blur=8, darken=0.4),
        "o.mp4")  # fmt: skip
    j = " ".join(img)
    assert "-loop 1" in j and "bg.jpg" in j and "gblur=sigma=8" in j and "force_original_aspect_ratio=increase" in j
    vid = " ".join(fr.build_command(
        fr.RenderSpec(1080, 1920, 30, 5.0, background="video", background_file="bg.mp4"), "o.mp4"))
    assert "-stream_loop -1" in vid
    with pytest.raises(FFmpegError, match="needs a file"):
        fr.build_command(fr.RenderSpec(1080, 1920, 30, 5.0, background="image"), "o.mp4")


# ------------------------------------------------------------------- make


def test_make_video_mp4_end_to_end(tmp_path):
    ws = Workspace.create(tmp_path / "jobs")
    events = []
    res = make_video(project(duration={"target_seconds": 5.5}), ws, engine=FakeEngine(), cache=False,
                     progress=events.append)
    assert res.video.name == "output.mp4" and res.video.stat().st_size > 10_000
    info = probe(res.video, "stream=codec_name,width,height,r_frame_rate:format=duration")
    video = next(s for s in info["streams"] if s.get("codec_name") == "h264")
    assert (video["width"], video["height"], video["r_frame_rate"]) == (1080, 1920, "30/1")
    assert float(info["format"]["duration"]) == pytest.approx(5.5, abs=0.3)
    assert res.target_met
    for f in (res.audio_wav, res.audio_mp3, res.captions_srt, res.captions_ass, res.words_json,
              res.project_file):
        assert f.is_file(), f
    assert (ws.path / "fonts" / "Montserrat-Black.ttf").is_file()
    assert ProjectConfig.load(res.project_file).script == SCRIPT
    stages = [e.stage for e in events]
    assert {"voice", "captions", "render", "done"} <= set(stages)
    fractions = [e.fraction for e in events]
    assert fractions == sorted(fractions) and fractions[-1] == 1.0


def test_captions_are_burned_in_and_in_sync(tmp_path):
    ws = Workspace.create(tmp_path / "jobs")
    res = make_video(project(captions={"preset": "bold-pop", "overrides": {
        "colors": {"highlight": "#FF0000"}}}), ws, engine=FakeEngine(), cache=False)
    words = json.loads(res.words_json.read_text(encoding="utf-8"))
    mid = (words[3]["start"] + words[3]["end"]) / 2
    frame = frame_at(res.video, mid)
    rgb = frame[..., :3].astype(int)
    red = ((rgb[..., 0] > 200) & (rgb[..., 1] < 60) & (rgb[..., 2] < 60)).sum()
    assert red > 500, "the active word should be drawn in the highlight colour"
    silence = frame_at(res.video, res.duration - 0.05)
    red_end = ((silence[..., 0] > 200) & (silence[..., 1] < 60) & (silence[..., 2] < 60)).sum()
    assert red_end == 0, "no caption after the narration ends"


def test_transparent_webm_and_mov_keep_alpha(tmp_path):
    for container, codec in (("webm", "libvpx-vp9"), ("mov", "prores")):
        ws = Workspace.create(tmp_path / f"jobs-{container}")
        res = make_video(
            project(background={"type": "transparent"}, export={"video": container, "quality": "fast"}),
            ws, engine=FakeEngine(), cache=False)
        words = json.loads(res.words_json.read_text(encoding="utf-8"))
        t = (words[2]["start"] + words[2]["end"]) / 2
        frame = frame_at(res.video, t, codec)
        alpha = frame[..., 3]
        assert (alpha > 200).sum() > 500, f"{container}: caption pixels must be opaque"
        assert (alpha == 0).sum() > frame.shape[0] * frame.shape[1] * 0.8, f"{container}: rest transparent"


def test_image_background_cover_crop(tmp_path):
    bg = tmp_path / "bg.png"
    Image.new("RGB", (400, 300), (200, 30, 30)).save(bg)
    ws = Workspace.create(tmp_path / "jobs")
    res = make_video(
        project(format="square", background={"type": "image", "path": str(bg)},
                export={"quality": "fast"}),
        ws, engine=FakeEngine(), cache=False)
    frame = frame_at(res.video, 0.05)
    assert frame.shape[:2] == (1080, 1080)
    assert frame[10, 10, 0] > 150 and frame[10, 10, 1] < 90  # red image fills the frame


def test_background_validation(tmp_path):
    ws = Workspace.create(tmp_path / "jobs")
    with pytest.raises(ScriptError, match="Choose a image file"):
        make_video(project(background={"type": "image"}), ws, engine=FakeEngine(), cache=False)
    with pytest.raises(ScriptError, match="not found"):
        make_video(project(background={"type": "video", "path": "nope.mp4"}), ws,
                   engine=FakeEngine(), cache=False)
    txt = tmp_path / "x.txt"
    txt.write_text("hi")
    with pytest.raises(ScriptError, match="must be one of"):
        make_video(project(background={"type": "image", "path": str(txt)}), ws,
                   engine=FakeEngine(), cache=False)


def test_audio_only_format_skips_video(tmp_path):
    ws = Workspace.create(tmp_path / "jobs")
    res = make_video(project(format="audio"), ws, engine=FakeEngine(), cache=False)
    assert res.video is None and res.captions_ass is None
    assert res.audio_mp3.is_file() and res.captions_srt.is_file()


def test_youtube_format_uses_landscape(tmp_path):
    ws = Workspace.create(tmp_path / "jobs")
    res = make_video(project(format="youtube", captions={"preset": "subtitle-classic"},
                             export={"quality": "fast"}), ws, engine=FakeEngine(), cache=False)
    info = probe(res.video, "stream=width,height")
    assert (info["streams"][0]["width"], info["streams"][0]["height"]) == (1920, 1080)


def test_rerender_reuses_voice_without_new_tts(tmp_path):
    ws = Workspace.create(tmp_path / "jobs")
    eng = FakeEngine()
    first = make_video(project(export={"quality": "fast"}), ws, engine=eng, cache=False)
    calls = eng.calls
    wav_stamp = first.audio_wav.stat().st_mtime_ns
    restyled = project(captions={"preset": "neon"}, export={"quality": "fast"})
    second = make_video(restyled, ws, engine=eng, cache=False, reuse_audio=True)
    assert eng.calls == calls
    assert second.audio_wav.stat().st_mtime_ns == wav_stamp
    assert second.duration == pytest.approx(first.duration)
    assert "Rubik" in second.captions_ass.read_text(encoding="utf-8")


def test_cancel_during_render(tmp_path):
    import threading

    ws = Workspace.create(tmp_path / "jobs")
    ev = threading.Event()

    def stop_when_rendering(e):
        if e.stage == "render":
            ev.set()

    with pytest.raises(JobCancelled):
        make_video(project(), ws, engine=FakeEngine(), cache=False, cancel=ev,
                   progress=stop_when_rendering)
    assert not (ws.path / "output.mp4").exists()


def test_missing_glyph_warning_reaches_result(tmp_path):
    ws = Workspace.create(tmp_path / "jobs")
    res = make_video(project(script="नमस्ते दुनिया। यह एक परीक्षण है।", format="audio"), ws,
                     engine=FakeEngine(), cache=False)
    assert res.video is None  # audio only: no caption warnings needed
    ws2 = Workspace.create(tmp_path / "jobs")
    res2 = make_video(project(script="नमस्ते दुनिया।", export={"quality": "fast"}), ws2,
                      engine=FakeEngine(), cache=False)
    assert any("Noto Sans Devanagari" in w for w in res2.warnings)


# ------------------------------------------------------------------ preview


def test_preview_frame_png_is_fast_and_matches_format():
    import time

    t0 = time.perf_counter()
    png = preview_frame(project(captions={"preset": "bold-pop"}))
    first = time.perf_counter() - t0
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    import io

    img = Image.open(io.BytesIO(png))
    assert img.size == (1080, 1920)
    arr = np.array(img.convert("RGB")).astype(int)
    yellow = ((arr[..., 0] > 220) & (arr[..., 1] > 200) & (arr[..., 2] < 80)).sum()
    assert yellow > 300  # the highlighted word is visible
    assert first < 5
    t1 = time.perf_counter()
    assert preview_frame(project(captions={"preset": "bold-pop"})) == png  # cached
    assert time.perf_counter() - t1 < 0.5


def test_preview_changes_with_style_and_rejects_audio():
    a = preview_frame(project(captions={"preset": "bold-pop"}))
    b = preview_frame(project(captions={"preset": "neon"}))
    assert a != b
    with pytest.raises(ScriptError, match="no caption preview"):
        preview_frame(project(format="audio"))


def test_preview_transparent_uses_neutral_backdrop():
    import io

    img = Image.open(io.BytesIO(preview_frame(project(background={"type": "transparent"}))))
    px = img.convert("RGB").getpixel((5, 5))
    assert all(abs(a - b) <= 4 for a, b in zip(px, (0x5A, 0x62, 0x70), strict=True))


# ---------------------------------------------------------------------- cli


def test_cli_formats_styles_fonts_json():
    assert len(json.loads(runner.invoke(app, ["formats", "--json"]).output)) == 5
    assert len(json.loads(runner.invoke(app, ["styles", "--json"]).output)) == 10
    assert len(json.loads(runner.invoke(app, ["fonts", "--json"]).output)) >= 15


def test_cli_preview_writes_png(tmp_path):
    script = tmp_path / "s.txt"
    script.write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / "p.png"
    res = runner.invoke(app, ["preview", str(script), "-o", str(out), "--style", "boxed",
                              "--set", "colors.highlight=#00FF00"])
    assert res.exit_code == 0, res.output
    assert Image.open(out).size == (1080, 1920)


def test_cli_make_with_fake_engine(tmp_path):
    from narrareel.engines import registry

    registry.register_engine("fake", "tests.unit.fake_engine:FakeEngine")
    script = tmp_path / "s.txt"
    script.write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / "video.mp4"
    res = runner.invoke(app, ["make", str(script), "--voice", "fake:v1", "--target", "10s",
                              "--style", "karaoke", "--quality", "fast", "-o", str(out), "--json"])
    try:
        assert res.exit_code == 0, res.output
        data = json.loads(res.output)
        assert out.is_file() and data["video"] == str(out) and data["target_met"] is True
        assert (tmp_path / "video.mp4").stat().st_size > 5000
    finally:
        registry.reset_instances()
        registry.ENGINES.pop("fake", None)


def test_cli_make_rejects_bad_input(tmp_path):
    script = tmp_path / "s.txt"
    script.write_text(SCRIPT, encoding="utf-8")
    assert "either --speed or --target" in runner.invoke(
        app, ["make", str(script), "--speed", "1.1", "--target", "10s"]).output
    assert "Unknown caption style" in runner.invoke(
        app, ["make", str(script), "--voice", "edge:en-US-AvaNeural", "--style", "nope", "--format", "reels"]
    ).output
    assert "--set expects key=value" in runner.invoke(
        app, ["preview", str(script), "--set", "oops"]).output
