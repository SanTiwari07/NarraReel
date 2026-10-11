import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

from narrareel import model_store
from narrareel.jobs.runner import JobRunner
from narrareel.server import create_app


@pytest.fixture
def stores(tmp_path, monkeypatch):
    """A fake hub cache with our two Chatterbox repos and someone else's model in it."""
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("NARRAREEL_MODEL_DIR", raising=False)
    # restored after the test, whatever apply() sets
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)
    default = tmp_path / "default-hub"
    monkeypatch.setenv("NARRAREEL_HF_DEFAULT", str(default))
    constants = sys.modules.get("huggingface_hub.constants")
    if constants is not None:
        monkeypatch.setattr(constants, "HF_HUB_CACHE", constants.HF_HUB_CACHE)
    for repo in (
        "models--ResembleAI--chatterbox",
        "models--ResembleAI--chatterbox-turbo",
        "models--Other--thing",
    ):
        (default / repo / "blobs").mkdir(parents=True)
        (default / repo / "blobs" / "weights").write_bytes(b"x" * 2048)
    return tmp_path, default


def test_defaults_to_the_hub_cache(stores):
    _, default = stores
    info = model_store.info()
    assert not info.chosen and model_store.hub_cache() == default
    assert info.models_gb >= 0 and info.needed_gb > 4


def test_choosing_a_folder_moves_only_our_models(stores):
    tmp, default = stores
    root = model_store.check_location(str(tmp / "D-drive" / "NarraReel models"))
    leftovers = model_store.set_location(root)
    new = root / "huggingface"
    assert leftovers == []
    assert (new / "models--ResembleAI--chatterbox" / "blobs" / "weights").is_file()
    assert (new / "models--ResembleAI--chatterbox-turbo").is_dir()
    assert not (default / "models--ResembleAI--chatterbox").exists()
    assert (default / "models--Other--thing").is_dir()  # other apps' models stay put
    # remembered, and the hub now downloads there
    assert model_store.hub_cache() == new and model_store.info().chosen
    assert os.environ["HF_HUB_CACHE"] == str(new)


def test_keeping_the_default_moves_nothing(stores):
    _, default = stores
    info = model_store.keep_default()
    assert info.chosen and model_store.hub_cache() == default
    assert (default / "models--ResembleAI--chatterbox").is_dir()


def test_bad_folders_are_refused_plainly(stores, monkeypatch):
    with pytest.raises(model_store.StorageError, match="full folder path"):
        model_store.check_location("models")
    with pytest.raises(model_store.StorageError, match="Choose a folder"):
        model_store.check_location("  ")
    monkeypatch.setenv("NARRAREEL_MODEL_DIR", str(stores[0] / "env"))
    with pytest.raises(model_store.StorageError, match="NARRAREEL_MODEL_DIR"):
        model_store.check_location(str(stores[0] / "elsewhere"))


def test_not_enough_room_on_another_drive_is_caught(stores, monkeypatch):
    monkeypatch.setattr(model_store, "_same_drive", lambda a, b: False)
    monkeypatch.setattr(model_store, "_free_gb", lambda p: 0.1)
    monkeypatch.setattr(model_store, "_size_gb", lambda p: 3.0)
    with pytest.raises(model_store.StorageError, match="0.1 GB free"):
        model_store.check_location(str(stores[0] / "small-drive"))


def test_storage_api(stores):
    tmp, _ = stores
    with TestClient(create_app(runner=JobRunner(tmp / "jobs"), static_dir=tmp / "no-ui")) as c:
        assert c.get("/api/storage/models").json()["chosen"] is False
        bad = c.put("/api/storage/models", json={"path": "relative"})
        assert bad.status_code == 422 and "full folder path" in bad.json()["error"]
        task = c.put("/api/storage/models", json={"path": str(tmp / "models")}).json()["task_id"]
        job = c.app.state.runner.get(task)
        end = time.time() + 20
        while not job.finished and time.time() < end:
            time.sleep(0.05)
        assert job.status == "done" and job.result["leftovers"] == []
        info = c.get("/api/storage/models").json()
        assert info["chosen"] and info["path"] == str(tmp / "models")
    with TestClient(create_app(runner=JobRunner(tmp / "j2"), demo=True)) as demo:
        assert demo.put("/api/storage/models", json={"path": str(tmp / "x")}).status_code == 403
