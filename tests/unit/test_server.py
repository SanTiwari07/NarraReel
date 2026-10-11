import io
import json
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from narrareel.audio import ffmpeg as ff
from narrareel.engines import registry
from narrareel.jobs.runner import JobRunner
from narrareel.server import create_app

pytestmark = pytest.mark.skipif(
    not (ff.available() and ff.has_libass()), reason="ffmpeg with libass needed"
)

SCRIPT = "Wake up early. Grind hard every single day, because success is waiting for you."
PROJECT = {"script": SCRIPT, "voice": {"engine": "fake", "voice_id": "v1"},
           "export": {"quality": "fast"}}  # fmt: skip


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))
    registry.register_engine("fake", "tests.unit.fake_engine:FakeEngine")
    runner = JobRunner(tmp_path / "jobs")
    with TestClient(create_app(runner=runner, static_dir=tmp_path / "no-ui")) as c:
        c.runner = runner
        yield c
    registry.reset_instances()
    registry.ENGINES.pop("fake", None)


def wait_for(client, job_id, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        data = client.get(f"/api/jobs/{job_id}").json()
        if data["status"] in ("done", "failed", "cancelled"):
            return data
        time.sleep(0.1)
    raise AssertionError("job did not finish")


# ------------------------------------------------------------------ system


def test_health(client):
    h = client.get("/api/health").json()
    assert h["ffmpeg"] and h["libass"] and h["version"]
    assert h["auth_required"] is False


def test_engines_and_voices(client):
    engines = {e["id"]: e for e in client.get("/api/engines").json()}
    assert engines["edge"]["status"]["available"]
    assert engines["edge"]["capabilities"]["native_word_timing"]
    voices = client.get("/api/voices", params={"engine": "edge", "language": "en-US"}).json()
    assert voices and voices[0]["ref"].startswith("edge:en-US")
    r = client.get("/api/voices", params={"engine": "nope"})
    assert r.status_code == 502 or r.status_code == 400
    assert "Unknown voice engine" in r.json()["error"]


def test_root_without_built_ui_explains(client):
    r = client.get("/")
    assert r.status_code == 200 and "not built" in r.json()["message"]


# ------------------------------------------------------------------ script


def test_analyze(client):
    r = client.post("/api/analyze", json={"text": SCRIPT + "\n\nA second paragraph here."})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["word_count"] == 18 and d["paragraph_count"] == 2 and d["sentence_count"] == 3
    assert d["estimate"]["total_seconds"] > 5
    assert len(d["sentences"]) == 3 and d["sentences"][0]["seconds"] > 0


def test_analyze_empty_script_is_zero_not_error(client):
    d = client.post("/api/analyze", json={"text": "  "}).json()
    assert d["word_count"] == 0 and d["sentences"] == []


def test_plan_with_target_string_and_seconds(client):
    a = client.post("/api/plan", json={"text": SCRIPT, "target": "30s"}).json()
    b = client.post("/api/plan", json={"text": SCRIPT, "target_seconds": 30}).json()
    assert a["plan"]["target_seconds"] == 30 == b["plan"]["target_seconds"]
    assert [o["kind"] for o in a["plan"]["options"]][0] in ("edit_script", "adjust_delivery")
    none = client.post("/api/plan", json={"text": SCRIPT}).json()
    assert [o["speed"] for o in none["plan"]["options"]] == [0.75, 1.0, 1.25, 1.5, 2.0]


def test_plan_errors(client):
    r = client.post("/api/plan", json={"text": "", "target": "30s"})
    assert r.status_code == 422 and "empty" in r.json()["error"]
    r = client.post("/api/plan", json={"text": SCRIPT, "target": "soon"})
    assert r.status_code == 422 and "not a valid duration" in r.json()["error"]


def test_parse_duration(client):
    d = client.post("/api/duration/parse", json={"text": "1m30s"}).json()
    assert d == {"seconds": 90.0, "formatted": "1:30"}
    assert client.post("/api/duration/parse", json={"text": "zzz"}).status_code == 422


def test_validation_errors_are_friendly(client):
    r = client.post("/api/analyze", json={})
    assert r.status_code == 422
    body = r.json()
    assert body["type"] == "ValidationError" and "text" in body["error"]


# ------------------------------------------------------------------ voices


def test_voice_preview_audio(client):
    r = client.post("/api/preview/voice", json={"text": SCRIPT, "voice": {"engine": "fake", "voice_id": "v1"}})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert len(r.content) > 2000


def test_voice_preview_unavailable_engine(client):
    r = client.post("/api/preview/voice", json={"text": SCRIPT, "voice": {"engine": "chatterbox", "voice_id": "x"}})
    assert r.status_code in (409, 400)


# ---------------------------------------------------------------- captions


def test_fonts_list_preview_upload(client):
    fonts = client.get("/api/fonts").json()
    assert len(fonts) >= 15 and {"id", "family", "license", "tags"} <= set(fonts[0])
    img = client.get("/api/fonts/anton-regular/preview.png", params={"text": "HELLO"})
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"
    assert client.get("/api/fonts/missing/preview.png").status_code == 422
    from narrareel.captions import fonts as fm

    data = fm.get_font("bangers-regular").path.read_bytes()
    up = client.post("/api/fonts", files={"file": ("Mine.ttf", data, "font/ttf")})
    assert up.status_code == 200 and up.json()["user"] is True
    assert any(f["user"] for f in client.get("/api/fonts").json())
    bad = client.post("/api/fonts", files={"file": ("x.ttf", b"nope", "font/ttf")})
    assert bad.status_code == 422


def test_presets_and_save_user_style(client):
    assert len(client.get("/api/presets/styles").json()) == 10
    assert {f["id"] for f in client.get("/api/presets/formats").json()} >= {"reels", "youtube"}
    r = client.post("/api/presets/styles", json={
        "name": "My Look", "preset": "boxed", "overrides": {"colors": {"text": "#00FF00"}}})
    assert r.status_code == 200 and r.json()["id"] == "my-look"
    styles = client.get("/api/presets/styles").json()
    assert any(s["id"] == "my-look" and s["colors"]["text"] == "#00FF00" for s in styles)
    bad = client.post("/api/presets/styles", json={"name": "x", "preset": "nope"})
    assert bad.status_code == 422


def test_preview_frame(client):
    r = client.post("/api/preview/frame", json={"project": PROJECT})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(r.content)).size == (1080, 1920)
    bad = client.post("/api/preview/frame",
                      json={"project": {**PROJECT, "captions": {"preset": "nope"}}})
    assert bad.status_code == 422 and "Unknown caption style" in bad.json()["error"]
    audio = client.post("/api/preview/frame", json={"project": {**PROJECT, "format": "audio"}})
    assert audio.status_code == 422


def test_background_upload_and_use(client):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (10, 200, 10)).save(buf, "PNG")
    up = client.post("/api/backgrounds", files={"file": ("bg.png", buf.getvalue(), "image/png")})
    assert up.status_code == 200, up.text
    path = up.json()["path"]
    r = client.post("/api/preview/frame", json={"project": {
        **PROJECT, "background": {"type": "image", "path": path}}})
    assert r.status_code == 200
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    px = img.getpixel((5, 5))
    assert px[1] > 150 and px[0] < 80


def test_background_upload_rejects_bad_files(client):
    assert client.post("/api/backgrounds", files={"file": ("a.exe", b"x", "application/octet-stream")}).status_code == 422
    fake = client.post("/api/backgrounds", files={"file": ("a.png", b"not an image", "image/png")})
    assert fake.status_code == 422 and "could not be read" in fake.json()["error"]


def test_arbitrary_server_paths_are_refused_as_backgrounds(client, tmp_path):
    secret = tmp_path / "secret.png"
    Image.new("RGB", (8, 8)).save(secret)
    r = client.post("/api/preview/frame", json={"project": {
        **PROJECT, "background": {"type": "image", "path": str(secret)}}})
    assert r.status_code == 422 and "Upload the background file again" in r.json()["error"]
    r = client.post("/api/jobs", json={"project": {
        **PROJECT, "background": {"type": "video", "path": str(secret)}}})
    assert r.status_code == 422


# --------------------------------------------------------------------- jobs


def test_job_lifecycle_sse_files_and_rerender(client):
    r = client.post("/api/jobs", json={"project": {**PROJECT, "duration": {"target_seconds": 5.5}}})
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    events = []
    with client.stream("GET", f"/api/jobs/{job_id}/events") as stream:
        name = None
        for line in stream.iter_lines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and name == "progress":
                events.append(json.loads(line.split(":", 1)[1]))
            elif line.startswith("data:") and name == "end":
                end = json.loads(line.split(":", 1)[1])
                break
    assert events[0]["stage"] in ("prepare", "voice")
    fractions = [e["fraction"] for e in events]
    assert fractions == sorted(fractions) and fractions[-1] == 1.0
    assert {"voice", "captions", "render", "done"} <= {e["stage"] for e in events}
    assert end["status"] == "done"

    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["status"] == "done" and status["result"]["target_met"] is True
    files = status["result"]["files"]
    assert files["video"] == "output.mp4" and "words_json" in files

    video = client.get(f"/api/jobs/{job_id}/files/output.mp4")
    assert video.status_code == 200 and video.headers["content-type"] == "video/mp4"
    assert len(video.content) > 5000
    part = client.get(f"/api/jobs/{job_id}/files/output.mp4", headers={"Range": "bytes=0-99"})
    assert part.status_code == 206 and len(part.content) == 100

    dl = client.get(f"/api/jobs/{job_id}/files/output.mp4", params={"download": "true"})
    assert "narrareel_wake-up-early_reels.mp4" in dl.headers["content-disposition"]
    srt = client.get(f"/api/jobs/{job_id}/files/captions.srt").text
    assert "-->" in srt
    words = client.get(f"/api/jobs/{job_id}/files/words.json").json()
    assert words[0]["source"] == "native"
    assert client.get(f"/api/jobs/{job_id}/files/log.txt").status_code == 404
    assert client.get(f"/api/jobs/{job_id}/files/..%2Fsecret").status_code in (404, 422)

    # restyle without re-synthesizing the voice
    eng_calls = registry.get_engine("fake").calls
    project = {**PROJECT, "duration": {"target_seconds": 5.5}, "captions": {"preset": "neon"}}
    re = client.post(f"/api/jobs/{job_id}/rerender", json={"project": project})
    assert re.status_code == 200
    new_id = re.json()["job_id"]
    assert new_id != job_id
    done = wait_for(client, new_id)
    assert done["status"] == "done"
    assert registry.get_engine("fake").calls == eng_calls

    recent = client.get("/api/jobs").json()
    assert [j["id"] for j in recent][:2] == [new_id, job_id]


def test_job_failure_is_reported_with_message(client):
    r = client.post("/api/jobs", json={"project": {**PROJECT, "script": "   "}})
    job_id = r.json()["job_id"]
    done = wait_for(client, job_id)
    assert done["status"] == "failed" and "empty" in done["error"]


def test_job_unknown_engine_fails_cleanly(client):
    r = client.post("/api/jobs", json={"project": {**PROJECT, "voice": {"engine": "zzz", "voice_id": "a"}}})
    done = wait_for(client, r.json()["job_id"])
    assert done["status"] == "failed" and "Unknown voice engine" in done["error"]


def test_cancel_queued_or_running_job(client):
    ids = [client.post("/api/jobs", json={"project": PROJECT}).json()["job_id"] for _ in range(3)]
    res = client.post(f"/api/jobs/{ids[2]}/cancel")
    assert res.status_code == 200
    final = wait_for(client, ids[2])
    assert final["status"] in ("cancelled", "done")
    for i in ids[:2]:
        wait_for(client, i)
    assert client.post("/api/jobs/nope/cancel").status_code == 404


def test_unknown_job_and_missing_narration_for_rerender(client):
    assert client.get("/api/jobs/nope").status_code == 404
    r = client.post("/api/jobs/20200101_000000_abcdef/rerender", json={"project": PROJECT})
    assert r.status_code == 400 and "no longer available" in r.json()["error"]


def test_project_validate(client):
    ok = client.post("/api/project/validate", json={"project": PROJECT})
    assert ok.status_code == 200 and ok.json()["format"] == "reels"
    bad = client.post("/api/project/validate", json={"project": {"script": 5}})
    assert bad.status_code == 422
    style = client.post("/api/project/validate",
                        json={"project": {**PROJECT, "captions": {"preset": "zzz"}}})
    assert style.status_code == 422


# --------------------------------------------------------------------- auth


def test_token_protects_api(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))
    with TestClient(create_app(runner=JobRunner(tmp_path / "jobs"), token="s3cret")) as c:
        assert c.get("/api/health").json()["auth_required"] is True
        assert c.get("/api/fonts").status_code == 401
        assert c.get("/api/fonts", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert c.get("/api/fonts", headers={"Authorization": "Bearer s3cret"}).status_code == 200
        assert c.get("/api/fonts", params={"token": "s3cret"}).status_code == 200


def test_cors_only_in_dev(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))
    origin = {"Origin": "http://localhost:5173"}
    with TestClient(create_app(runner=JobRunner(tmp_path / "j"))) as c:
        assert "access-control-allow-origin" not in c.get("/api/health", headers=origin).headers
    with TestClient(create_app(runner=JobRunner(tmp_path / "j2"), dev=True)) as c:
        assert c.get("/api/health", headers=origin).headers["access-control-allow-origin"] == origin["Origin"]


def test_static_ui_served_with_spa_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (static / "assets" / "a.js").write_text("console.log(1)", encoding="utf-8")
    with TestClient(create_app(runner=JobRunner(tmp_path / "j"), static_dir=static)) as c:
        assert c.get("/").text == "<html>app</html>"
        assert c.get("/voice").text == "<html>app</html>"  # client-side route
        assert c.get("/assets/a.js").text == "console.log(1)"
        assert c.get("/api/nope").status_code == 404
        assert c.get("/../../etc/passwd").text == "<html>app</html>"


def test_engine_prepare_task_reports_progress(client):
    class Downloady(registry.get_engine("fake").__class__):
        def prepare(self, progress=None):
            for i in range(1, 5):
                progress(i / 4, f"Downloading {i}/4")

    registry.get_engine("fake")  # ensure instance exists
    registry._instances["fake"] = Downloady()
    r = client.post("/api/engines/fake/prepare")
    assert r.status_code == 200
    task_id = r.json()["task_id"]
    end = None
    with client.stream("GET", f"/api/tasks/{task_id}/events") as stream:
        name = None
        for line in stream.iter_lines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and name == "end":
                end = json.loads(line.split(":", 1)[1])
                break
    assert end and end["status"] == "done"


def test_demo_mode_limits(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))
    registry.register_engine("fake", "tests.unit.fake_engine:FakeEngine")
    try:
        with TestClient(create_app(runner=JobRunner(tmp_path / "j"), demo=True,
                                   static_dir=tmp_path / "no-ui")) as c:
            assert c.get("/api/health").json()["demo"] is True
            assert c.get("/api/fonts").status_code == 200
            for method, path in (("post", "/api/fonts"), ("post", "/api/backgrounds"),
                                 ("post", "/api/voices/clone"), ("post", "/api/engines/kokoro/prepare"),
                                 ("delete", "/api/voices/custom/x"), ("post", "/api/presets/styles")):
                r = getattr(c, method)(path)
                assert r.status_code == 403 and "public demo" in r.json()["error"], path
            long_script = "word " * 400
            r = c.post("/api/jobs", json={"project": {**PROJECT, "script": long_script}})
            assert r.status_code == 422 and "limited to 350 words" in r.json()["error"]
            ok = c.post("/api/jobs", json={"project": PROJECT})
            assert ok.status_code == 200
    finally:
        registry.reset_instances()
        registry.ENGINES.pop("fake", None)
