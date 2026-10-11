import io
import json
import threading

import pytest
from fastapi.testclient import TestClient

from narrareel.engines import installer, registry
from narrareel.errors import EngineError, JobCancelled
from narrareel.jobs.runner import JobRunner
from narrareel.models import EngineStatus
from narrareel.server import create_app


class FakePip:
    """Stands in for ``subprocess.Popen`` running ``python -m pip install``."""

    def __init__(self, lines, code=0):
        self.stdout = io.StringIO("".join(f"{line}\n" for line in lines))
        self.code = code
        self.terminated = False
        self.cmd = None

    def __call__(self, cmd, **_kwargs):
        self.cmd = cmd
        return self

    def wait(self):
        return self.code

    def terminate(self):
        self.terminated = True


PIP_OUTPUT = [
    "Collecting chatterbox-tts>=0.1.7",
    "  Downloading chatterbox_tts-0.1.7-py3-none-any.whl (200 kB)",
    "Collecting torch==2.6.0",
    "  Downloading torch-2.6.0-cp313-cp313-win_amd64.whl (204.2 MB)",
    "Installing collected packages: torch, chatterbox-tts",
    "Successfully installed chatterbox-tts-0.1.7 torch-2.6.0",
]


def test_requirements_come_from_the_extra():
    clone = installer.requirements_for("clone")
    assert any(r.startswith("chatterbox-tts") for r in clone)
    assert all("extra" not in r for r in clone)
    assert any(r.startswith("kokoro-onnx") for r in installer.requirements_for("offline"))


def test_install_streams_progress_and_succeeds(monkeypatch):
    pip = FakePip(PIP_OUTPUT)
    monkeypatch.setattr(installer.subprocess, "Popen", pip)
    seen: list[tuple[float, str]] = []
    installer.install_extra("clone", lambda f, m: seen.append((f, m)), threading.Event())
    assert pip.cmd[1:4] == ["-m", "pip", "install"]
    assert any(a.startswith("chatterbox-tts") for a in pip.cmd)
    assert any("torch-2.6.0" in m and "204.2 MB" in m for _, m in seen)
    fractions = [f for f, _ in seen]
    assert fractions == sorted(fractions) and fractions[-1] == 1.0


def test_install_failure_is_explained(monkeypatch):
    monkeypatch.setattr(installer.subprocess, "Popen", FakePip(["ERROR: No matching distribution"], code=1))
    with pytest.raises(EngineError, match="did not finish.*No matching distribution"):
        installer.install_extra("clone", lambda *_: None, threading.Event())


def test_install_without_pip_says_what_to_do(monkeypatch):
    monkeypatch.setattr(installer.subprocess, "Popen", FakePip(["/python: No module named pip"], code=1))
    with pytest.raises(EngineError, match="ensurepip"):
        installer.install_extra("clone", lambda *_: None, threading.Event())


def test_install_can_be_cancelled(monkeypatch):
    pip = FakePip(PIP_OUTPUT)
    monkeypatch.setattr(installer.subprocess, "Popen", pip)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(JobCancelled):
        installer.install_extra("clone", lambda *_: None, cancel)
    assert pip.terminated


def test_second_install_is_refused_while_one_runs(monkeypatch):
    monkeypatch.setattr(installer.subprocess, "Popen", FakePip(PIP_OUTPUT))
    assert installer._running.acquire(blocking=False)
    try:
        with pytest.raises(EngineError, match="already running"):
            installer.install_extra("clone", lambda *_: None, threading.Event())
    finally:
        installer._running.release()


class _Missing:
    def status(self):
        return EngineStatus(available=False, reason="not installed")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))
    monkeypatch.setitem(registry._instances, "chatterbox", _Missing())
    with TestClient(create_app(runner=JobRunner(tmp_path / "jobs"), static_dir=tmp_path / "no-ui")) as c:
        yield c
    registry.reset_instances()


def _end_event(client, task_id):
    with client.stream("GET", f"/api/tasks/{task_id}/events") as stream:
        name = None
        for line in stream.iter_lines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and name == "end":
                return json.loads(line.split(":", 1)[1])


def test_install_endpoint_runs_a_task(client, monkeypatch):
    monkeypatch.setattr(installer.subprocess, "Popen", FakePip(PIP_OUTPUT))
    r = client.post("/api/engines/chatterbox/install")
    assert r.status_code == 200
    assert _end_event(client, r.json()["task_id"])["status"] == "done"


def test_install_endpoint_reports_a_failed_install(client, monkeypatch):
    monkeypatch.setattr(installer.subprocess, "Popen", FakePip(["ERROR: boom"], code=1))
    end = _end_event(client, client.post("/api/engines/chatterbox/install").json()["task_id"])
    assert end["status"] == "failed" and "boom" in end["error"]


def test_install_endpoint_rejects_unknown_and_installed_engines(client, monkeypatch):
    assert client.post("/api/engines/edge/install").status_code == 502
    monkeypatch.setitem(registry._instances, "chatterbox", type("Ok", (), {
        "status": lambda self: EngineStatus(available=True)})())
    r = client.post("/api/engines/chatterbox/install")
    assert r.status_code == 502 and "already installed" in r.json()["error"]
