"""Where the big downloaded models live (the voice-cloning weights are several GB).

The cloning model comes from the Hugging Face hub, which keeps its own
cache (``~/.cache/huggingface/hub`` by default, usually on the system drive). People with a
small or full C: drive need to put it elsewhere, so NarraReel lets them pick a folder and
points the hub cache there (D31). Order: ``NARRAREEL_MODEL_DIR``, then the folder chosen in
the app (saved in ``~/.narrareel/storage.json``), then the hub's own default.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import config
from .errors import NarraReelError

log = logging.getLogger("narrareel.model_store")

#: hub repos NarraReel downloads (chatterbox and chatterbox-turbo); only these are moved
OUR_REPOS = ("models--ResembleAI--chatterbox",)
#: what the cloning models need on disk (original + turbo, measured 2026-10-11)
CLONE_MODEL_GB = 7.0


class StorageError(NarraReelError):
    """The chosen folder cannot hold the models."""


@dataclass(frozen=True)
class StorageInfo:
    path: str
    default_path: str
    chosen: bool
    from_env: bool
    free_gb: float | None
    models_gb: float
    needed_gb: float


def _prefs_file() -> Path:
    return config.home_dir() / "storage.json"


def _prefs() -> dict:
    try:
        data = json.loads(_prefs_file().read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _saved_dir() -> str | None:
    return _prefs().get("model_dir") or None


def _save_prefs(data: dict) -> None:
    prefs = _prefs_file()
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text(json.dumps(data, indent=2), "utf-8")


def keep_default() -> StorageInfo:
    """The person looked at the default folder and kept it: remember that, move nothing."""
    if os.environ.get("NARRAREEL_MODEL_DIR"):
        raise StorageError(
            "The model folder is set by NARRAREEL_MODEL_DIR. Change or remove that variable instead."
        )
    _save_prefs({"keep_default": True})
    apply()
    return info()


def default_hub_cache() -> Path:
    """The hub's own default, ignoring anything NarraReel set."""
    if os.environ.get("NARRAREEL_HF_DEFAULT"):
        return Path(os.environ["NARRAREEL_HF_DEFAULT"])
    hf_home = os.environ.get("HF_HOME")
    base = Path(hf_home).expanduser() if hf_home else Path.home() / ".cache" / "huggingface"
    return base / "hub"


def hub_cache() -> Path:
    """The hub cache NarraReel uses right now."""
    env = os.environ.get("NARRAREEL_MODEL_DIR")
    chosen = env or _saved_dir()
    return Path(chosen).expanduser() / "huggingface" if chosen else default_hub_cache()


def apply() -> Path:
    """Point the Hugging Face hub at the chosen folder. Safe to call any number of times."""
    path = hub_cache()
    if "NARRAREEL_HF_DEFAULT" not in os.environ:
        # remember the real default before we override HF_HUB_CACHE, so moving back works
        os.environ["NARRAREEL_HF_DEFAULT"] = str(
            Path(os.environ["HF_HUB_CACHE"])
            if os.environ.get("HF_HUB_CACHE")
            else default_hub_cache()
        )
    os.environ["HF_HUB_CACHE"] = str(path)
    constants = sys.modules.get("huggingface_hub.constants")
    if constants is not None:  # already imported: the hub reads this attribute on every download
        constants.HF_HUB_CACHE = str(path)  # type: ignore[attr-defined]
    return path


def _size_gb(folder: Path) -> float:
    total = 0
    for root, _, files in os.walk(folder):
        for name in files:
            p = Path(root) / name
            if not p.is_symlink():
                with contextlib.suppress(OSError):
                    total += p.stat().st_size
    return total / 1024**3


def _our_repos(cache: Path) -> list[Path]:
    if not cache.is_dir():
        return []
    return [p for p in cache.iterdir() if p.is_dir() and p.name.startswith(OUR_REPOS)]


def _free_gb(path: Path) -> float | None:
    probe = path
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free / 1024**3
    except OSError:
        return None


def info() -> StorageInfo:
    cache = hub_cache()
    env = bool(os.environ.get("NARRAREEL_MODEL_DIR"))
    chosen = os.environ.get("NARRAREEL_MODEL_DIR") or _saved_dir()
    downloaded = sum(_size_gb(p) for p in _our_repos(cache))
    return StorageInfo(
        path=str(Path(chosen).expanduser()) if chosen else str(cache),
        default_path=str(default_hub_cache()),
        chosen=bool(chosen) or bool(_prefs().get("keep_default")),
        from_env=env,
        free_gb=None if (free := _free_gb(cache)) is None else round(free, 1),
        models_gb=round(downloaded, 1),
        needed_gb=CLONE_MODEL_GB,
    )


def check_location(folder: str) -> Path:
    """Validate a folder the person typed or picked. Returns it as a path; raises ``StorageError``."""
    if os.environ.get("NARRAREEL_MODEL_DIR"):
        raise StorageError(
            "The model folder is set by NARRAREEL_MODEL_DIR. Change or remove that variable instead."
        )
    raw = folder.strip().strip('"')
    if not raw:
        raise StorageError("Choose a folder first.")
    root = Path(raw).expanduser()
    if not root.is_absolute():
        raise StorageError("Use a full folder path, for example D:\\NarraReel models.")
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".narrareel-write-test"
        probe.write_text("ok", "utf-8")
        probe.unlink()
    except OSError as exc:
        raise StorageError(f"NarraReel cannot write to {root}: {exc.strerror or exc}.") from exc
    new_cache = root / "huggingface"
    old_cache = hub_cache()
    if _same(old_cache, new_cache):
        return root
    need = sum(_size_gb(p) for p in _our_repos(old_cache) if not (new_cache / p.name).exists())
    free = _free_gb(root)
    if need and not _same_drive(old_cache, new_cache) and free is not None and free < need + 0.5:
        raise StorageError(
            f"{root} has {free:.1f} GB free, but the models already downloaded need {need:.1f} GB."
        )
    return root


def _same(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return False


def _same_drive(a: Path, b: Path) -> bool:
    return a.resolve().anchor.lower() == b.resolve().anchor.lower()


def _move_repo(src: Path, dest: Path) -> bool:
    """Move one downloaded repo. Returns False if the old copy could not be fully removed."""
    try:
        os.replace(src, dest)  # same drive: instant
        return True
    except OSError:
        pass  # another drive, or files in use (Windows keeps a loaded model's files open)
    partial = dest.with_name(dest.name + ".partial")
    shutil.rmtree(partial, ignore_errors=True)
    shutil.copytree(src, partial, symlinks=True)
    partial.rename(dest)
    shutil.rmtree(src, ignore_errors=True)
    return not src.exists()


def set_location(root: Path, progress=None) -> list[str]:
    """Use ``root`` (already checked) from now on and move the models NarraReel downloaded there.

    Returns the old folders that could not be removed, so the person can delete them later.
    """
    old_cache = hub_cache()
    new_cache = root / "huggingface"
    leftovers: list[str] = []
    if not _same(old_cache, new_cache):
        repos = [p for p in _our_repos(old_cache) if not (new_cache / p.name).exists()]
        new_cache.mkdir(parents=True, exist_ok=True)
        for i, repo in enumerate(repos):
            if progress:
                name = repo.name.split("--")[-1]
                progress(0.05 + 0.9 * i / len(repos), f"Moving {name} ({_size_gb(repo):.1f} GB)")
            log.info("moving %s to %s", repo, new_cache)
            if not _move_repo(repo, new_cache / repo.name):
                leftovers.append(str(repo))
    _save_prefs({"model_dir": str(root)})
    apply()
    if progress:
        progress(1.0, "Done")
    return leftovers


_PICKER = r"""
import sys, tkinter
from tkinter import filedialog
root = tkinter.Tk()
root.withdraw()
root.attributes("-topmost", True)
path = filedialog.askdirectory(initialdir=sys.argv[1] or None, mustexist=False,
                               title="Where should NarraReel keep the voice model?")
root.destroy()
sys.stdout.write(path or "")
"""


def pick_folder(initial: str | None = None) -> str | None:
    """Open the system folder picker on this computer. ``None`` if the person cancelled.

    Runs in its own process: Tk must own the main thread, and the server's threads do not.
    """
    try:
        done = subprocess.run(  # noqa: S603 - our own interpreter and a fixed script
            [sys.executable, "-c", _PICKER, initial or ""],
            capture_output=True, text=True, timeout=600,
        )  # fmt: skip
    except subprocess.TimeoutExpired as exc:
        raise StorageError("The folder window was open too long. Try again.") from exc
    if done.returncode != 0:
        log.warning("folder picker failed: %s", done.stderr.strip()[-300:])
        raise StorageError(
            "This computer cannot show a folder window here. Type the folder path instead."
        )
    return done.stdout.strip() or None
