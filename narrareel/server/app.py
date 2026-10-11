"""FastAPI app factory (WHAT_TO_DO.md sections 5.14 and 5.15).

The server is a thin layer over the core: routes validate input, call core functions and
return their pydantic models. Bound to loopback by default; see ``create_app(token=...)``.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import mimetypes
import re
from collections.abc import AsyncIterator
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from sse_starlette.sse import EventSourceResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__, config, model_store
from .. import voices as voices_mod
from ..audio import ffmpeg as ff
from ..captions import fonts as fonts_mod
from ..captions.formats import FormatError, list_formats
from ..captions.styles import (
    StyleError,
    get_style,
    list_styles,
    resolve_style,
    save_user_style,
)
from ..engines import installer, registry
from ..errors import (
    DependencyMissing,
    EngineError,
    EngineUnavailable,
    FFmpegError,
    NarraReelError,
    ScriptError,
)
from ..jobs.runner import Job, JobRunner
from ..models import ProgressEvent, VoiceSelection
from ..pipeline.make import export_name, preview_frame
from ..pipeline.speak import preview_audio
from ..project import ProjectConfig
from ..script import analyze_script, format_duration, parse_duration, plan
from ..script import duration as dur
from . import schemas as S

log = logging.getLogger("narrareel.server")

DEMO_MAX_WORDS = 350
MAX_FONT_BYTES = 10 * 1024 * 1024
MAX_BACKGROUND_BYTES = 150 * 1024 * 1024
DOWNLOADABLE = {
    "output.mp4", "output.webm", "output.mov", "voice.mp3", "voice.wav", "captions.srt",
    "captions.ass", "words.json", "project.narrareel.json",
}  # fmt: skip
SAMPLE_TEXT = {
    "en": "Every great video starts with a simple idea.",
    "hi": "नमस्ते, यह मेरी आवाज़ का एक छोटा सा नमूना है।",
}


def _status_for(exc: NarraReelError) -> int:
    if isinstance(
        exc,
        ScriptError
        | StyleError
        | FormatError
        | fonts_mod.FontError
        | voices_mod.VoiceProfileError
        | model_store.StorageError,
    ):
        return 422
    if isinstance(exc, EngineUnavailable | DependencyMissing):
        return 409
    if isinstance(exc, EngineError | FFmpegError):
        return 502
    return 400


def _error(exc_or_msg: Exception | str, status: int, kind: str, details: list | None = None):
    return JSONResponse(
        {"error": str(exc_or_msg), "type": kind, "details": details}, status_code=status
    )


def _uploads_dir() -> Path:
    path = config.home_dir() / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_app(
    *,
    runner: JobRunner | None = None,
    dev: bool = False,
    token: str | None = None,
    static_dir: Path | None = None,
    demo: bool = False,
) -> FastAPI:
    runner = runner or JobRunner()
    model_store.apply()  # downloads go to the model folder the person chose

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        runner.shutdown()

    app = FastAPI(
        lifespan=lifespan,
        title="NarraReel",
        version=__version__,
        description="Script in, Reel out. Local API behind the NarraReel web app.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.runner = runner

    # ------------------------------------------------------------ plumbing

    if dev:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if demo:

        @app.middleware("http")
        async def demo_limits(request: Request, call_next):
            path = request.url.path
            blocked = (
                request.method != "GET"
                and path.startswith(("/api/fonts", "/api/backgrounds", "/api/voices/clone",
                                    "/api/voices/custom", "/api/engines/", "/api/presets/styles",
                                    "/api/storage"))
            )  # fmt: skip
            if blocked:
                return _error(
                    "This is the public demo, so uploads, cloning and downloads of models are turned off. "
                    "Install NarraReel on your computer to use them.", 403, "DemoLimit"
                )
            return await call_next(request)

    if token:

        @app.middleware("http")
        async def require_token(request: Request, call_next):
            if request.url.path.startswith("/api/") and request.url.path != "/api/health":
                header = request.headers.get("authorization", "")
                supplied = header[7:] if header.lower().startswith("bearer ") else None
                supplied = supplied or request.query_params.get("token")
                if supplied != token:
                    return _error("A valid access token is required.", 401, "Unauthorized")
            return await call_next(request)

    @app.exception_handler(NarraReelError)
    async def narrareel_error(_: Request, exc: NarraReelError):
        return _error(exc, _status_for(exc), type(exc).__name__)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = f"{where}: {first.get('msg', 'invalid input')}" if where else "Invalid input."
        return _error(msg, 422, "ValidationError", json.loads(json.dumps(exc.errors(), default=str)))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        return _error(exc.detail, exc.status_code, "HTTPError")

    # -------------------------------------------------------------- health

    @app.get("/api/health", response_model=S.HealthResponse, tags=["system"])
    def health() -> S.HealthResponse:
        from ..timing import align

        have = ff.available()
        return S.HealthResponse(
            demo=demo,
            version=__version__,
            ffmpeg=have,
            ffmpeg_version=ff.version() if have else None,
            libass=ff.has_libass() if have else False,
            align_available=align.is_available(),
            auth_required=bool(token),
        )

    # ------------------------------------------------------------- engines

    @app.get("/api/engines", tags=["voices"])
    def engines() -> list[dict[str, Any]]:
        return [i.model_dump() for i in registry.available_engines()]

    @app.post("/api/engines/{engine_id}/prepare", response_model=S.TaskCreated, tags=["voices"])
    def prepare_engine(engine_id: str) -> S.TaskCreated:
        engine = registry.get_engine(engine_id)
        status = engine.status()
        if not status.available:
            raise EngineUnavailable(status.reason or f"{engine_id} is not available.")

        def run(progress, cancel):
            def on(fraction: float, message: str) -> None:
                if cancel.is_set():
                    from ..errors import JobCancelled

                    raise JobCancelled("Cancelled.")
                progress(ProgressEvent(stage="prepare", fraction=fraction, message=message))

            engine.prepare(on)
            return {"engine": engine_id}

        return S.TaskCreated(task_id=runner.submit_task("prepare", run).id)

    @app.post("/api/engines/{engine_id}/install", response_model=S.TaskCreated, tags=["voices"])
    def install_engine(engine_id: str) -> S.TaskCreated:
        extra = installer.EXTRAS.get(engine_id)
        if extra is None:
            raise EngineError(f"'{engine_id}' has nothing to install.")
        if registry.get_engine(engine_id).status().available:
            raise EngineError(f"'{engine_id}' is already installed.")

        def run(progress, cancel):
            def on(fraction: float, message: str) -> None:
                progress(ProgressEvent(stage="prepare", fraction=fraction, message=message))

            installer.install_extra(extra, on, cancel)
            return {"engine": engine_id}

        return S.TaskCreated(task_id=runner.submit_task("install", run).id)

    # ------------------------------------------------------------- storage

    @app.get("/api/storage/models", response_model=S.ModelStorage, tags=["system"])
    def model_storage() -> S.ModelStorage:
        return S.ModelStorage(**asdict(model_store.info()))

    @app.post("/api/storage/models/browse", response_model=S.FolderPicked, tags=["system"])
    def browse_model_folder() -> S.FolderPicked:
        # opens the system folder window on the computer NarraReel runs on
        return S.FolderPicked(path=model_store.pick_folder(model_store.info().path))

    @app.post("/api/storage/models/keep", response_model=S.ModelStorage, tags=["system"])
    def keep_model_folder() -> S.ModelStorage:
        return S.ModelStorage(**asdict(model_store.keep_default()))

    @app.put("/api/storage/models", response_model=S.TaskCreated, tags=["system"])
    def set_model_storage(req: S.ModelFolderRequest) -> S.TaskCreated:
        root = model_store.check_location(req.path)  # fails fast: bad path, read-only, no room

        def run(progress, cancel):
            def on(fraction: float, message: str) -> None:
                progress(ProgressEvent(stage="prepare", fraction=fraction, message=message))

            leftovers = model_store.set_location(root, on)
            return {"path": str(root), "leftovers": leftovers}

        return S.TaskCreated(task_id=runner.submit_task("storage", run).id)

    # -------------------------------------------------------------- voices

    @app.get("/api/voices", tags=["voices"])
    def voices(engine: str | None = None, language: str | None = None) -> list[dict[str, Any]]:
        return [v.model_dump() | {"ref": v.ref} for v in registry.list_voices(engine, language)]

    @app.get("/api/voices/{engine}/{voice_id}/sample", tags=["voices"])
    def voice_sample(engine: str, voice_id: str) -> Response:
        from ..audio.process import encode_mp3, write_wav

        eng = registry.get_engine(engine)
        info = eng.get_voice(voice_id)
        lang = "hi" if info and info.language.lower().startswith("hi") else "en"
        cache = config.cache_dir() / "voice_samples"
        cache.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{engine}__{voice_id}")
        mp3 = cache / f"{safe}.mp3"
        if not mp3.is_file():
            audio = preview_audio(
                SAMPLE_TEXT[lang], VoiceSelection(engine=engine, voice_id=voice_id), max_sentences=1
            )
            wav = cache / f"{safe}.wav"
            write_wav(wav, audio)
            encode_mp3(wav, mp3, "128k")
            wav.unlink(missing_ok=True)
        return FileResponse(mp3, media_type="audio/mpeg")

    # ------------------------------------------------------- voice cloning

    async def _read_upload(file: UploadFile, limit: int = voices_mod.MAX_UPLOAD_BYTES) -> bytes:
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise ScriptError("That recording is larger than 25 MB.")
        return data

    @app.get("/api/voices/guided-text", tags=["voices"])
    def guided_text() -> dict[str, str]:
        return {**voices_mod.GUIDED_TEXTS, "consent": voices_mod.CONSENT_TEXT}

    @app.post("/api/voices/clone/check", response_model=voices_mod.QualityReport, tags=["voices"])
    async def clone_check(file: UploadFile = File(...)) -> voices_mod.QualityReport:
        data = await _read_upload(file)
        return await asyncio.to_thread(voices_mod.check_recording, data)

    @app.post("/api/voices/clone", response_model=S.CloneResult, tags=["voices"])
    async def clone_voice(
        file: UploadFile = File(...),
        name: str = Form(...),
        consent: bool = Form(False),
        language: str = Form("en"),
    ) -> S.CloneResult:
        data = await _read_upload(file)
        profile, report = await asyncio.to_thread(
            voices_mod.create_profile, data, name, consent, language
        )
        return S.CloneResult(profile=profile, quality=report)

    @app.get("/api/voices/custom", tags=["voices"])
    def custom_voices() -> list[voices_mod.VoiceProfile]:
        return voices_mod.list_profiles()

    @app.delete("/api/voices/custom/{voice_id}", tags=["voices"])
    def delete_custom_voice(voice_id: str) -> dict[str, bool]:
        voices_mod.delete_profile(voice_id)
        return {"deleted": True}

    @app.get("/api/voices/custom/{voice_id}/reference.mp3", tags=["voices"])
    def custom_reference(voice_id: str) -> FileResponse:
        voices_mod.get_profile(voice_id)
        path = voices_mod.profile_dir(voice_id) / "reference.mp3"
        if not path.is_file():
            raise HTTPException(404, "No recording is stored for that voice.")
        return FileResponse(path, media_type="audio/mpeg")

    @app.get("/api/voices/custom/{voice_id}/export", tags=["voices"])
    def export_custom_voice(voice_id: str) -> Response:
        data = voices_mod.export_profile(voice_id)
        return Response(
            data, media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{voice_id}.narrareel-voice.zip"'},
        )  # fmt: skip

    @app.post("/api/voices/custom/import", response_model=voices_mod.VoiceProfile, tags=["voices"])
    async def import_custom_voice(file: UploadFile = File(...)) -> voices_mod.VoiceProfile:
        data = await _read_upload(file, 60 * 1024 * 1024)
        return await asyncio.to_thread(voices_mod.import_profile, data)

    # ---------------------------------------------------- script analysis

    def _cps(voice: str | None, language: str) -> tuple[float, str]:
        return dur.get_cps(voice, language)

    @app.post("/api/analyze", response_model=S.AnalyzeResponse, tags=["script"])
    def analyze(req: S.AnalyzeRequest) -> S.AnalyzeResponse:
        a = analyze_script(req.text)
        cps, basis = _cps(req.voice, a.language_hint)
        est = dur.estimate(a, cps, 1.0, 1.0, basis)
        sentences = []
        for s in a.sentences:
            toks = a.tokens[s.token_start : s.token_end]
            chars = sum(1 for t in toks for ch in t.text if ch.isalnum())
            sentences.append(
                S.SentenceInfo(
                    idx=s.idx, text=s.text, words=len(toks), seconds=chars / cps,
                    paragraph_idx=s.paragraph_idx,
                )
            )  # fmt: skip
        return S.AnalyzeResponse(
            word_count=a.word_count, char_count=a.char_count, sentence_count=len(a.sentences),
            paragraph_count=a.paragraph_count, language_hint=a.language_hint,
            warnings=a.warnings, sentences=sentences, estimate=est, cps=cps,
        )  # fmt: skip

    @app.post("/api/plan", response_model=S.PlanResponse, tags=["script"])
    def make_plan(req: S.PlanRequest) -> S.PlanResponse:
        a = analyze_script(req.text)
        if a.word_count == 0:
            raise ScriptError("Your script is empty. Paste or type some text first.")
        target = req.target_seconds or (parse_duration(req.target) if req.target else None)
        cps, basis = _cps(req.voice, a.language_hint)
        return S.PlanResponse(plan=plan(a, cps, target, basis), cps=cps)

    @app.post("/api/duration/parse", response_model=S.ParseDurationResponse, tags=["script"])
    def parse(req: S.ParseDurationRequest) -> S.ParseDurationResponse:
        seconds = parse_duration(req.text)
        return S.ParseDurationResponse(seconds=seconds, formatted=format_duration(seconds))

    # ------------------------------------------------------------ previews

    @app.post("/api/preview/voice", tags=["preview"])
    def preview_voice(req: S.VoicePreviewRequest) -> Response:
        import numpy as np

        from ..audio.process import encode_mp3, write_wav

        audio = preview_audio(req.text, req.voice, max_sentences=2)
        key = hashlib.sha1(np.ascontiguousarray(audio).tobytes()).hexdigest()[:12]
        folder = config.cache_dir() / "voice_previews"
        folder.mkdir(parents=True, exist_ok=True)
        wav, mp3 = folder / f"{key}.wav", folder / f"{key}.mp3"
        if not mp3.is_file():
            write_wav(wav, audio)
            encode_mp3(wav, mp3, "128k")
            wav.unlink(missing_ok=True)
        return Response(mp3.read_bytes(), media_type="audio/mpeg")

    @app.post("/api/preview/frame", tags=["preview"])
    def preview_frame_route(req: S.FramePreviewRequest) -> Response:
        _check_background(req.project)
        png = preview_frame(req.project, at=req.at, word_index=req.word_index)
        return Response(png, media_type="image/png")

    # --------------------------------------------------------------- fonts

    @app.get("/api/fonts", tags=["captions"])
    def list_fonts(tag: str | None = None) -> list[dict[str, Any]]:
        return [f.public() for f in fonts_mod.list_fonts(tag)]

    @app.get("/api/fonts/{font_id}/preview.png", tags=["captions"])
    def font_preview(font_id: str, text: str = Query("THIS IS YOUR CAPTION", max_length=80)) -> Response:
        png = fonts_mod.preview_png(fonts_mod.get_font(font_id), text)
        return Response(png, media_type="image/png", headers={"Cache-Control": "max-age=86400"})

    @app.post("/api/fonts", tags=["captions"])
    async def upload_font(file: UploadFile = File(...)) -> dict[str, Any]:
        data = await file.read(MAX_FONT_BYTES + 1)
        if len(data) > MAX_FONT_BYTES:
            raise fonts_mod.FontError("That font file is larger than 10 MB.")
        return fonts_mod.add_user_font(data, file.filename or "font.ttf").public()

    # ------------------------------------------------------------- presets

    @app.get("/api/presets/styles", tags=["captions"])
    def styles() -> list[dict[str, Any]]:
        return [s.model_dump(by_alias=True) for s in list_styles()]

    @app.get("/api/presets/formats", tags=["captions"])
    def formats() -> list[dict[str, Any]]:
        return [f.model_dump() for f in list_formats()]

    @app.post("/api/presets/styles", tags=["captions"])
    def save_style(req: S.StylePresetRequest) -> dict[str, Any]:
        style = resolve_style(req.preset, req.overrides, req.font)
        style = style.model_copy(update={"name": req.name})
        path = save_user_style(style)
        return get_style(path.stem).model_dump(by_alias=True)

    # ------------------------------------------------------------- uploads

    @app.post("/api/backgrounds", response_model=S.UploadResult, tags=["captions"])
    async def upload_background(file: UploadFile = File(...)) -> S.UploadResult:
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", file.filename or "background")
        suffix = Path(name).suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            kind = "image"
        elif suffix in {".mp4", ".mov", ".webm", ".mkv", ".m4v"}:
            kind = "video"
        else:
            raise ScriptError("Backgrounds must be an image (png, jpg, webp) or a video (mp4, mov, webm).")
        tmp = _uploads_dir() / f".upload-{hashlib.sha1(name.encode()).hexdigest()[:8]}{suffix}"
        size = 0
        with tmp.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BACKGROUND_BYTES:
                    out.close()
                    tmp.unlink(missing_ok=True)
                    raise ScriptError("That file is larger than 150 MB.")
                out.write(chunk)
        try:  # validate by decoding, not by extension
            probe = ff.probe_duration if kind == "video" else _probe_image
            await asyncio.to_thread(probe, tmp)
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            raise ScriptError(f"'{file.filename}' could not be read as {kind} ({exc}).") from exc
        digest = hashlib.sha1(tmp.read_bytes()[:1_000_000] + str(size).encode()).hexdigest()[:8]
        final = _uploads_dir() / f"{digest}_{name}"
        tmp.replace(final)
        return S.UploadResult(path=str(final), type=kind, name=name, size=size)

    def _probe_image(path: Path) -> None:
        from PIL import Image

        with Image.open(path) as im:
            im.verify()

    def _check_demo_length(script: str) -> None:
        if demo and analyze_script(script).word_count > DEMO_MAX_WORDS:
            raise ScriptError(
                f"The public demo is limited to {DEMO_MAX_WORDS} words (about two minutes). "
                "Install NarraReel on your computer for longer scripts."
            )

    def _check_background(project: ProjectConfig) -> None:
        """Only files uploaded through the API may be used as backgrounds."""
        bg = project.background
        if bg.type in ("image", "video"):
            if not bg.path:
                raise ScriptError(f"Choose a {bg.type} file for the background.")
            try:
                inside = Path(bg.path).resolve().is_relative_to(_uploads_dir().resolve())
            except OSError:
                inside = False
            if not inside:
                raise ScriptError("Upload the background file again; it is not available to the server.")

    # ------------------------------------------------------------- project

    @app.post("/api/project/validate", response_model=ProjectConfig, tags=["project"])
    def validate_project(req: S.ValidateProjectRequest) -> ProjectConfig:
        try:
            project = ProjectConfig.model_validate(req.project)
        except ValueError as exc:
            raise ScriptError(f"This is not a valid NarraReel project: {exc}") from exc
        resolve_style(project.captions.preset, project.captions.overrides, project.captions.font)
        return project

    # ---------------------------------------------------------------- jobs

    @app.post("/api/jobs", response_model=S.JobCreated, tags=["jobs"])
    def create_job(req: S.JobRequest) -> S.JobCreated:
        _check_demo_length(req.project.script)
        _check_background(req.project)
        resolve_style(req.project.captions.preset, req.project.captions.overrides,
                      req.project.captions.font)  # fail fast on bad style/font ids
        return S.JobCreated(job_id=runner.submit_video(req.project).id)

    @app.get("/api/jobs", tags=["jobs"])
    def recent_jobs(limit: int = Query(20, ge=1, le=100)) -> list[dict[str, Any]]:
        return runner.recent(limit)

    def _job(job_id: str) -> Job:
        job = runner.get(job_id)
        if job is None:
            raise HTTPException(404, "That job doesn't exist (the app may have been restarted).")
        return job

    @app.get("/api/jobs/{job_id}", tags=["jobs"])
    def job_status(job_id: str) -> dict[str, Any]:
        job = runner.get(job_id)
        if job is not None:
            return job.public()
        folder = runner.workspace_for(job_id)
        if folder and (folder / "job.json").is_file():
            return json.loads((folder / "job.json").read_text(encoding="utf-8"))
        raise HTTPException(404, "That job doesn't exist.")

    async def _event_stream(job: Job) -> AsyncIterator[dict[str, str]]:
        sent = 0
        while True:
            fresh = job.events_after(sent)
            for ev in fresh:
                sent += 1
                yield {"event": "progress", "data": ev.model_dump_json()}
            if job.finished and not job.events_after(sent):
                yield {"event": "end", "data": json.dumps(job.public())}
                return
            await asyncio.sleep(0.15)

    @app.get("/api/jobs/{job_id}/events", tags=["jobs"])
    async def job_events(job_id: str) -> EventSourceResponse:
        return EventSourceResponse(_event_stream(_job(job_id)))

    @app.get("/api/tasks/{task_id}/events", tags=["jobs"])
    async def task_events(task_id: str) -> EventSourceResponse:
        return EventSourceResponse(_event_stream(_job(task_id)))

    @app.post("/api/jobs/{job_id}/cancel", tags=["jobs"])
    def cancel_job(job_id: str) -> dict[str, bool]:
        _job(job_id)
        return {"cancelled": runner.cancel(job_id)}

    @app.post("/api/jobs/{job_id}/rerender", response_model=S.JobCreated, tags=["jobs"])
    def rerender(job_id: str, req: S.JobRequest) -> S.JobCreated:
        _check_demo_length(req.project.script)
        _check_background(req.project)
        return S.JobCreated(job_id=runner.submit_video(req.project, reuse_from=job_id).id)

    @app.get("/api/jobs/{job_id}/files/{name}", tags=["jobs"])
    def job_file(job_id: str, name: str, download: bool = False) -> FileResponse:
        if name not in DOWNLOADABLE:
            raise HTTPException(404, "No such file.")
        folder = runner.workspace_for(job_id)
        path = folder / name if folder else None
        if path is None or not path.is_file():
            raise HTTPException(404, "That file isn't available (yet).")
        media = mimetypes.guess_type(name)[0] or "application/octet-stream"
        filename = None
        if download:
            filename = name
            try:
                proj = json.loads((folder / "project.narrareel.json").read_text(encoding="utf-8"))
                stem = export_name(proj.get("script", ""), proj.get("format", "reels"), "x")[:-2]
                filename = f"{stem}{Path(name).suffix}" if name.startswith("output") else f"{stem}_{name}"
            except (OSError, ValueError):
                pass
        return FileResponse(path, media_type=media, filename=filename)

    # -------------------------------------------------------------- static

    static = static_dir or (config.package_dir() / "server" / "static")
    index = static / "index.html"
    if index.is_file():
        from fastapi.staticfiles import StaticFiles

        assets = static / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(404, "Unknown API route.")
            candidate = (static / full_path).resolve()
            if full_path and candidate.is_file() and candidate.is_relative_to(static.resolve()):
                return FileResponse(candidate)
            return FileResponse(index)

    else:

        @app.get("/", include_in_schema=False)
        def no_ui() -> JSONResponse:
            return JSONResponse(
                {
                    "message": "NarraReel API is running, but the web app is not built.",
                    "hint": "Run `npm run build` in frontend/ or use `narrareel serve --dev` "
                    "with the Vite dev server. API docs: /api/docs",
                }
            )

    return app
