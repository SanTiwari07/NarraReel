"""One-click install of an optional extra from the web app (the same packages as ``pip install "narrareel[clone]"``)."""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import math
import re
import subprocess
import sys
import threading
from collections import deque
from collections.abc import Callable

from ..errors import EngineError, JobCancelled

log = logging.getLogger("narrareel.engines.installer")

ProgressFn = Callable[[float, str], None]

#: engine id -> the pyproject extra that provides it
EXTRAS: dict[str, str] = {"chatterbox": "clone", "kokoro": "offline"}

# used only when narrareel's own metadata is unreadable (a source checkout that was never installed)
_FALLBACK: dict[str, list[str]] = {
    "clone": ["chatterbox-tts>=0.1.7", "setuptools<81"],
    "offline": ["kokoro-onnx>=0.6"],
}

_running = threading.Lock()


def requirements_for(extra: str) -> list[str]:
    """The requirement strings of ``narrareel[extra]``, read from the installed package metadata."""
    try:
        requires = importlib.metadata.requires("narrareel") or []
    except importlib.metadata.PackageNotFoundError:
        requires = []
    found = []
    for line in requires:
        spec, _, marker = line.partition(";")
        if re.search(rf"""extra\s*==\s*['"]{re.escape(extra)}['"]""", marker):
            found.append(spec.strip())
    return found or _FALLBACK[extra]


def _step(line: str) -> str | None:
    """A short, readable status for the pip output lines worth showing."""
    m = re.match(r"(Collecting|Downloading)\s+(\S+)", line)
    if m:
        name = m.group(2).rsplit("/", 1)[-1]
        size = re.search(r"\(([\d.]+ [kMG]B)\)", line)
        return f"{'Downloading' if m.group(1) == 'Downloading' else 'Finding'} {name}" + (
            f" ({size.group(1)})" if size else ""
        )
    if line.startswith("Installing collected packages"):
        return "Installing, almost done"
    return None


def install_extra(extra: str, progress: ProgressFn, cancel: threading.Event) -> None:
    """Run ``pip install`` for the extra in this Python, streaming progress. Raises ``EngineError``."""
    if not _running.acquire(blocking=False):
        raise EngineError("An install is already running. Wait for it to finish.")
    try:
        requirements = requirements_for(extra)
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--progress-bar", "off", "--disable-pip-version-check", "--no-input",
            *requirements,
        ]  # fmt: skip
        log.info("installing: %s", " ".join(cmd))
        progress(0.02, "Starting the install")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(  # noqa: S603 - our own interpreter and pinned requirement names
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
            creationflags=flags,
        )  # fmt: skip
        tail: deque[str] = deque(maxlen=6)
        steps = 0
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.strip()
            if not line:
                continue
            tail.append(line)
            if cancel.is_set():
                proc.terminate()
                proc.wait()
                raise JobCancelled("Cancelled. Nothing was changed if the install had not finished.")
            message = _step(line)
            if message:
                steps += 1
                # pip does not know the total, so ease towards 95% instead of guessing one
                fraction = 0.95 * (1 - math.exp(-steps / 40))
                progress(max(0.03, fraction), message)
        if proc.wait() != 0:
            detail = " ".join(tail)
            if "No module named pip" in detail:
                raise EngineError(
                    "This Python has no pip, so NarraReel cannot install it for you. "
                    "Run: python -m ensurepip, then try again."
                )
            raise EngineError(
                "The install did not finish. Check your internet connection and free disk space "
                f"(this needs about 3 GB), then try again. Last pip message: {tail[-1] if tail else 'none'}"
            )
        importlib.invalidate_caches()
        progress(1.0, "Installed")
    finally:
        _running.release()
