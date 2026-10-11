"""Request/response models for the HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..models import (
    DurationEstimate,
    DurationPlan,
    ScriptWarning,
    VoiceSelection,
)
from ..project import ProjectConfig
from ..voices import QualityReport, VoiceProfile


class HealthResponse(BaseModel):
    version: str
    ffmpeg: bool
    ffmpeg_version: str | None = None
    libass: bool
    align_available: bool
    auth_required: bool = False
    demo: bool = False


class AnalyzeRequest(BaseModel):
    text: str
    voice: str | None = Field(None, description="engine:voice, used for the speaking-rate estimate")


class SentenceInfo(BaseModel):
    idx: int
    text: str
    words: int
    seconds: float
    paragraph_idx: int


class AnalyzeResponse(BaseModel):
    word_count: int
    char_count: int
    sentence_count: int
    paragraph_count: int
    language_hint: str
    warnings: list[ScriptWarning]
    sentences: list[SentenceInfo]
    estimate: DurationEstimate
    cps: float


class PlanRequest(BaseModel):
    text: str
    voice: str | None = None
    target_seconds: float | None = Field(None, gt=0)
    target: str | None = Field(None, description="e.g. 90s, 6m, 6:00 (used if target_seconds is empty)")


class PlanResponse(BaseModel):
    plan: DurationPlan
    cps: float


class ParseDurationRequest(BaseModel):
    text: str


class ParseDurationResponse(BaseModel):
    seconds: float
    formatted: str


class VoicePreviewRequest(BaseModel):
    text: str
    voice: VoiceSelection


class FramePreviewRequest(BaseModel):
    project: ProjectConfig
    at: float | None = Field(None, ge=0)
    word_index: int | None = Field(None, ge=0)


class JobRequest(BaseModel):
    project: ProjectConfig


class JobCreated(BaseModel):
    job_id: str


class TaskCreated(BaseModel):
    task_id: str


class ModelStorage(BaseModel):
    """Where the voice-cloning model is (or will be) downloaded."""

    path: str
    default_path: str
    chosen: bool
    from_env: bool
    free_gb: float | None
    models_gb: float
    needed_gb: float


class ModelFolderRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1024)


class FolderPicked(BaseModel):
    path: str | None


class ValidateProjectRequest(BaseModel):
    project: dict[str, Any]


class UploadResult(BaseModel):
    path: str
    type: str
    name: str
    size: int


class StylePresetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    preset: str = "bold-pop"
    overrides: dict[str, Any] = Field(default_factory=dict)
    font: str | None = None


class ErrorResponse(BaseModel):
    error: str
    type: str
    details: list[Any] | None = None


class CloneResult(BaseModel):
    profile: VoiceProfile
    quality: QualityReport
