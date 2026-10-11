"""Background job queue with progress events and cancellation (WHAT_TO_DO.md section 5.13).

One worker thread (ML models and GPU memory do not like parallel jobs); extra jobs wait in
a queue. Progress is kept in memory and mirrored to ``job.json`` / ``log.txt`` in the job folder.
"""

from __future__ import annotations

import json
import logging
import queue
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ..errors import JobCancelled, NarraReelError
from ..models import ProgressEvent
from ..project import ProjectConfig
from .workspace import Workspace, list_jobs

log = logging.getLogger("narrareel.jobs")

Status = Literal["queued", "running", "done", "failed", "cancelled"]
RERENDER_FILES = ("voice.wav", "voice.mp3", "words.json", "project.json", "captions.srt")


@dataclass
class Job:
    id: str
    kind: str = "video"  # "video" | "prepare" | "install"
    status: Status = "queued"
    events: list[ProgressEvent] = field(default_factory=list)
    error: str | None = None
    result: dict[str, Any] | None = None
    created: float = field(default_factory=time.time)
    cancel: threading.Event = field(default_factory=threading.Event)
    workspace: Workspace | None = None
    project: ProjectConfig | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def finished(self) -> bool:
        return self.status in ("done", "failed", "cancelled")

    @property
    def last_event(self) -> ProgressEvent | None:
        return self.events[-1] if self.events else None

    def add_event(self, event: ProgressEvent) -> None:
        with self._lock:
            self.events.append(event)

    def events_after(self, index: int) -> list[ProgressEvent]:
        with self._lock:
            return list(self.events[index:])

    def public(self) -> dict[str, Any]:
        last = self.last_event
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "error": self.error,
            "fraction": last.fraction if last else 0.0,
            "message": last.message if last else "",
            "stage": last.stage if last else None,
            "result": self.result,
            "created": self.created,
        }


TaskFn = Callable[[Callable[[ProgressEvent], None], threading.Event], dict[str, Any] | None]


class JobRunner:
    def __init__(self, jobs_base: Path | None = None):
        self.jobs_base = jobs_base
        self._jobs: dict[str, Job] = {}
        self._queue: queue.Queue[tuple[Job, TaskFn] | None] = queue.Queue()
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._stopped = False

    # ------------------------------------------------------------ lifecycle

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._stopped = False
                self._worker = threading.Thread(
                    target=self._loop, name="narrareel-jobs", daemon=True
                )
                self._worker.start()

    def shutdown(self) -> None:
        self._stopped = True
        for job in list(self._jobs.values()):
            if not job.finished:
                job.cancel.set()
        self._queue.put(None)

    def _loop(self) -> None:
        while not self._stopped:
            item = self._queue.get()
            if item is None:
                return
            job, fn = item
            if job.cancel.is_set():
                self._finish(job, "cancelled", error="Cancelled before it started.")
                continue
            job.status = "running"
            self._persist(job)
            try:
                result = fn(job.add_event, job.cancel)
                job.result = result
                self._finish(job, "done")
            except JobCancelled:
                self._finish(job, "cancelled", error="Cancelled.")
            except NarraReelError as exc:
                log.info("Job %s failed: %s", job.id, exc)
                self._finish(job, "failed", error=str(exc))
            except Exception as exc:  # never let the worker die
                log.exception("Job %s crashed", job.id)
                self._finish(job, "failed", error=f"Unexpected error: {exc}")

    def _finish(self, job: Job, status: Status, error: str | None = None) -> None:
        job.status = status
        job.error = error
        stage = "done" if status == "done" else "error"
        last = job.last_event
        job.add_event(
            ProgressEvent(
                stage=stage,  # type: ignore[arg-type]
                fraction=1.0 if status == "done" else (last.fraction if last else 0.0),
                message="Done" if status == "done" else (error or status),
                detail={"status": status},
            )
        )
        self._persist(job)

    def _persist(self, job: Job) -> None:
        if job.workspace is None:
            return
        try:
            job.workspace.write_json("job.json", {**job.public(), "result": job.result})
        except OSError:
            log.debug("could not write job.json for %s", job.id)

    # --------------------------------------------------------------- submit

    def _register(self, job: Job) -> Job:
        with self._lock:
            self._jobs[job.id] = job
        return job

    def submit_video(
        self,
        project: ProjectConfig,
        *,
        reuse_from: str | None = None,
        runner_fn: Callable[..., Any] | None = None,
    ) -> Job:
        """Queue a video job. With ``reuse_from`` the narration of that job is reused."""
        from ..pipeline.make import make_video

        make = runner_fn or make_video
        ws = Workspace.create(self.jobs_base)
        reuse = False
        if reuse_from:
            src = self.workspace_for(reuse_from)
            if src is None or not (src / "voice.wav").is_file():
                raise NarraReelError(
                    "The narration of that video is no longer available. Generate it again."
                )
            for name in RERENDER_FILES:
                if (src / name).is_file():
                    shutil.copyfile(src / name, ws.file(name))
            reuse = True
        job = Job(id=ws.id, kind="video", workspace=ws, project=project)
        ws.write_json("project.input.json", json.loads(project.model_dump_json()))

        def run(progress, cancel):
            with ws.logging():
                res = make(project, ws, progress=progress, cancel=cancel, reuse_audio=reuse)
            return _result_summary(res)

        self._register(job)
        self._ensure_worker()
        self._persist(job)
        self._queue.put((job, run))
        return job

    def submit_task(self, kind: str, fn: TaskFn) -> Job:
        """Queue any long-running task (e.g. a model download)."""
        job = Job(id=f"{kind}-{int(time.time() * 1000):x}", kind=kind)
        self._register(job)
        self._ensure_worker()
        self._queue.put((job, fn))
        return job

    # --------------------------------------------------------------- lookup

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.finished:
            return False
        job.cancel.set()
        return True

    def workspace_for(self, job_id: str) -> Path | None:
        job = self._jobs.get(job_id)
        if job and job.workspace:
            return job.workspace.path
        base = self.jobs_base
        if base is None:
            from .. import config

            base = config.jobs_dir()
        path = base / job_id
        return path if path.is_dir() and "/" not in job_id and "\\" not in job_id else None

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Jobs in memory plus older ones found on disk (job.json), newest first."""
        seen: dict[str, dict[str, Any]] = {j.id: j.public() for j in self._jobs.values()
                                           if j.kind == "video"}
        for folder in list_jobs(self.jobs_base)[:limit]:
            if folder.name in seen:
                continue
            meta = folder / "job.json"
            if meta.is_file():
                try:
                    seen[folder.name] = json.loads(meta.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
        return sorted(seen.values(), key=lambda j: j["id"], reverse=True)[:limit]


def _result_summary(res: Any) -> dict[str, Any]:
    files = {
        "video": res.video,
        "audio_wav": res.audio_wav,
        "audio_mp3": res.audio_mp3,
        "captions_srt": res.captions_srt,
        "captions_ass": res.captions_ass,
        "words_json": res.words_json,
        "project": res.project_file,
    }
    return {
        "files": {k: v.name for k, v in files.items() if v is not None},
        "duration": res.duration,
        "target_seconds": res.target_seconds,
        "target_met": res.target_met,
        "note": res.note,
        "warnings": res.warnings,
    }
