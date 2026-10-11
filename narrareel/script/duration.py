"""Duration estimation and targeting (WHAT_TO_DO.md section 5.2). Pure Python."""

from __future__ import annotations

import contextlib
import json
import re
from dataclasses import dataclass

from .. import config
from ..errors import ScriptError
from ..models import (
    DurationEstimate,
    DurationOption,
    DurationPlan,
    Quality,
    ScriptAnalysis,
)

# Characters (letters, digits and combining marks) per second at 1.0x. English and Hindi are
# estimates; Tamil (11.8) was measured over two ta-IN Edge voices (11.9 and 11.6 cps).
DEFAULT_CPS = {"en": 14.0, "hi": 12.0, "ta": 11.8}
FALLBACK_CPS = 14.0
PRESET_SPEEDS = (0.75, 1.0, 1.25, 1.5, 2.0)
MIN_SPEED, MAX_SPEED = 0.5, 2.0


@dataclass(frozen=True)
class Pause:
    default: float
    min: float
    max: float

    def at(self, scale: float) -> float:
        return min(self.max, max(self.min, self.default * scale))


SENTENCE_PAUSE = Pause(0.35, 0.15, 1.00)
PARAGRAPH_PAUSE = Pause(0.80, 0.40, 1.80)
LEAD_PAUSE = Pause(0.25, 0.10, 0.50)
TAIL_PAUSE = Pause(0.40, 0.20, 1.00)

# Scale range over which pauses actually change (all at min ... all at max).
SCALE_MIN = 0.40
SCALE_MAX = 2.90


# ------------------------------------------------------------------ parsing


_UNIT_SECONDS = {"h": 3600, "hr": 3600, "m": 60, "min": 60, "s": 1, "sec": 1}
_PART = re.compile(r"(\d+(?:\.\d+)?)\s*(hr|h|min|m|sec|s)(?![a-z])", re.IGNORECASE)


def parse_duration(text: str) -> float:
    """``6m``, ``6:00``, ``1:02:00``, ``90s``, ``90``, ``1m30s``, ``1.5m`` -> seconds."""
    raw = (text or "").strip().lower()
    if not raw:
        raise ScriptError("Enter a duration like 90s, 6m, 1m30s or 6:00.")
    seconds: float
    if ":" in raw:
        parts = raw.split(":")
        if len(parts) > 3 or not all(re.fullmatch(r"\d+(\.\d+)?", p) for p in parts):
            raise ScriptError(f"'{text}' is not a valid duration. Try 6:00 or 1:02:00.")
        seconds = 0.0
        for p in parts:
            seconds = seconds * 60 + float(p)
    elif re.fullmatch(r"\d+(\.\d+)?", raw):
        seconds = float(raw)
    else:
        cleaned = _PART.sub("", raw).replace(" ", "")
        parts = _PART.findall(raw)
        if not parts or cleaned:
            raise ScriptError(f"'{text}' is not a valid duration. Try 90s, 6m or 1m30s.")
        seconds = sum(float(n) * _UNIT_SECONDS[u.lower()] for n, u in parts)
    if seconds <= 0:
        raise ScriptError("The target duration must be longer than zero.")
    return seconds


def format_duration(seconds: float) -> str:
    """308.7 -> ``5:09``; 3723 -> ``1:02:03``."""
    total = int(round(max(0.0, seconds)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ----------------------------------------------------------------- quality


def speed_quality(speed: float) -> Quality:
    if 0.90 <= speed <= 1.15:
        return "natural"
    if 0.80 <= speed < 0.90 or 1.15 < speed <= 1.30:
        return "noticeable"
    if 0.70 <= speed < 0.80 or 1.30 < speed <= 1.50:
        return "strong"
    return "not_recommended"


def _speed_message(speed: float, quality: Quality) -> str:
    if quality == "natural":
        return "Sounds natural."
    direction = "slow" if speed < 1 else "fast"
    if quality == "noticeable":
        return "Listeners may notice, but it's fine."
    if quality == "strong":
        return f"Sounds noticeably {direction}. Editing the script is better."
    return "This will sound unnatural. Edit the script instead."


# -------------------------------------------------------------- calibration


def default_cps(language: str) -> float:
    return DEFAULT_CPS.get(language, FALLBACK_CPS)


def _calibration_path():
    return config.cache_dir() / "calibration.json"


def _read_calibration() -> dict:
    try:
        return json.loads(_calibration_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get_cps(voice_ref: str | None, language: str = "en") -> tuple[float, str]:
    """Characters per second at 1.0x for a voice. Returns (cps, basis)."""
    if voice_ref:
        entry = _read_calibration().get(voice_ref)
        if isinstance(entry, dict) and float(entry.get("cps", 0)) > 1:
            return float(entry["cps"]), "calibrated"
    return default_cps(language), "default"


def update_calibration(voice_ref: str, chars: int, speech_seconds: float, speed: float) -> float:
    """Fold one real measurement into the running average and return the new cps."""
    if chars <= 0 or speech_seconds <= 0 or speed <= 0:
        raise ValueError("chars, speech_seconds and speed must be positive")
    measured = chars / (speech_seconds * speed)
    data = _read_calibration()
    entry = data.get(voice_ref) or {}
    n = min(int(entry.get("n", 0)), 19)
    old = float(entry.get("cps", measured))
    cps = (old * n + measured) / (n + 1)
    data[voice_ref] = {"cps": round(cps, 3), "n": n + 1}
    # Calibration is an optimisation; never fail a job because of it.
    with contextlib.suppress(OSError):
        _calibration_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return cps


# ---------------------------------------------------------------- estimate


def pause_seconds(analysis: ScriptAnalysis, scale: float = 1.0) -> float:
    total = LEAD_PAUSE.at(scale) + TAIL_PAUSE.at(scale)
    sentences = analysis.sentences
    for _i, s in enumerate(sentences[:-1]):
        total += (PARAGRAPH_PAUSE if s.ends_paragraph else SENTENCE_PAUSE).at(scale)
    return total


def speech_seconds(analysis: ScriptAnalysis, cps: float, speed: float = 1.0) -> float:
    return analysis.char_count / (cps * speed)


def estimate(
    analysis: ScriptAnalysis,
    cps: float | None = None,
    speed: float = 1.0,
    pause_scale: float = 1.0,
    basis: str = "default",
) -> DurationEstimate:
    cps = cps or default_cps(analysis.language_hint)
    speech = speech_seconds(analysis, cps, speed)
    pauses = pause_seconds(analysis, pause_scale)
    total = speech + pauses
    wpm = analysis.word_count / (total / 60) if total > 0 else 0.0
    return DurationEstimate(
        speech_seconds=speech,
        pause_seconds=pauses,
        total_seconds=total,
        words_per_minute=wpm,
        basis="calibrated" if basis == "calibrated" else "default",
    )


# -------------------------------------------------------------------- plan


def _scale_for_pause_total(analysis: ScriptAnalysis, wanted: float) -> float:
    """Pause scale whose pause total equals ``wanted`` seconds (bisection; monotonic)."""
    lo, hi = SCALE_MIN, SCALE_MAX
    if wanted <= pause_seconds(analysis, lo):
        return lo
    if wanted >= pause_seconds(analysis, hi):
        return hi
    for _ in range(60):
        mid = (lo + hi) / 2
        if pause_seconds(analysis, mid) < wanted:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _option_total(analysis: ScriptAnalysis, cps: float, speed: float, scale: float) -> float:
    return speech_seconds(analysis, cps, speed) + pause_seconds(analysis, scale)


def plan(
    analysis: ScriptAnalysis,
    cps: float | None = None,
    target_seconds: float | None = None,
    basis: str = "default",
) -> DurationPlan:
    """Build the options shown in the Duration step (section 5.2.3)."""
    cps = cps or default_cps(analysis.language_hint)
    est = estimate(analysis, cps, 1.0, 1.0, basis)
    speech_1x = est.speech_seconds

    if not target_seconds:
        opts = []
        for sp in PRESET_SPEEDS:
            q = speed_quality(sp)
            opts.append(
                DurationOption(
                    kind="speed_only",
                    speed=sp,
                    pause_scale=1.0,
                    resulting_seconds=_option_total(analysis, cps, sp, 1.0),
                    quality=q,
                    message=_speed_message(sp, q),
                )
            )
        return DurationPlan(
            estimate_1x=est,
            target_seconds=None,
            options=opts,
            recommended=PRESET_SPEEDS.index(1.0),
        )

    target = float(target_seconds)
    options: list[DurationOption] = []
    diff = target - est.total_seconds
    wps = analysis.word_count / est.total_seconds if est.total_seconds > 0 else 0.0

    has_a = abs(diff) > 0.03 * target
    if has_a:
        delta = round(diff * wps)
        verb = "Add" if delta > 0 else "Cut"
        options.append(
            DurationOption(
                kind="edit_script",
                speed=1.0,
                pause_scale=1.0,
                words_delta=delta,
                resulting_seconds=target,
                quality="natural",
                message=f"{verb} about {abs(delta)} words to reach {format_duration(target)} "
                "at natural speed.",
            )
        )

    # Option B - adjust delivery: pauses first, then speed.
    if diff >= 0:
        pause_cap = pause_seconds(analysis, SCALE_MAX)
        need = target - speech_1x
        if need <= pause_cap:
            scale, speed = _scale_for_pause_total(analysis, need), 1.0
        else:
            scale = SCALE_MAX
            remaining = target - (speech_1x + pause_cap)
            speed = speech_1x / (speech_1x + remaining)
    else:
        pause_floor = pause_seconds(analysis, SCALE_MIN)
        need = target - speech_1x
        if need >= pause_floor:
            scale, speed = _scale_for_pause_total(analysis, need), 1.0
        else:
            scale = SCALE_MIN
            remaining = (speech_1x + pause_floor) - target
            denom = speech_1x - remaining
            speed = speech_1x / denom if denom > 0 else MAX_SPEED
    options.append(_delivery_option("adjust_delivery", analysis, cps, speed, scale, target))

    # Option C - speed only.
    pause_1x = pause_seconds(analysis, 1.0)
    avail = target - pause_1x
    speed_c = speech_1x / avail if avail > 0 else MAX_SPEED
    options.append(_delivery_option("speed_only", analysis, cps, speed_c, 1.0, target))

    b_index = 1 if has_a else 0
    recommended = b_index if options[b_index].quality in ("natural", "noticeable") else 0
    return DurationPlan(
        estimate_1x=est,
        target_seconds=target,
        options=options,
        recommended=recommended,
    )


def _delivery_option(
    kind: str,
    analysis: ScriptAnalysis,
    cps: float,
    speed: float,
    scale: float,
    target: float,
) -> DurationOption:
    clamped = min(MAX_SPEED, max(MIN_SPEED, speed))
    quality = speed_quality(clamped)
    message = _speed_message(clamped, quality)
    resulting = _option_total(analysis, cps, clamped, scale)
    if abs(resulting - target) > 0.03 * target:
        quality = "not_recommended"
        cut = max(0, round((resulting - target) * analysis.word_count / max(resulting, 1e-6)))
        message = (
            f"This script can't fit in {format_duration(target)}. "
            + (f"Cut about {cut} words." if resulting > target else "Add more text.")
        )
    return DurationOption(
        kind=kind,  # type: ignore[arg-type]
        speed=round(clamped, 4),
        pause_scale=round(scale, 4),
        resulting_seconds=resulting,
        quality=quality,
        message=message,
    )


# ------------------------------------------------- pause layout (pipeline)

INTRA_PAUSE = 0.10  # between the parts of one long sentence that was split for synthesis


def pause_layout(analysis: ScriptAnalysis, units, scale: float) -> tuple[float, list[float], float]:
    """(lead, pauses after each synthesis unit except the last, tail) at a pause scale."""
    pauses: list[float] = []
    for a, b in zip(units, units[1:], strict=False):
        if a.sentence_idx == b.sentence_idx:
            pauses.append(INTRA_PAUSE)
        else:
            kind = PARAGRAPH_PAUSE if analysis.sentences[a.sentence_idx].ends_paragraph else SENTENCE_PAUSE
            pauses.append(kind.at(scale))
    return LEAD_PAUSE.at(scale), pauses, TAIL_PAUSE.at(scale)


def layout_total(analysis: ScriptAnalysis, units, scale: float) -> float:
    lead, pauses, tail = pause_layout(analysis, units, scale)
    return lead + sum(pauses) + tail


def solve_pause_scale(analysis: ScriptAnalysis, units, wanted_total: float) -> float:
    """Scale whose pause layout adds up to ``wanted_total`` seconds (clamped to the valid range)."""
    lo, hi = SCALE_MIN, SCALE_MAX
    if wanted_total <= layout_total(analysis, units, lo):
        return lo
    if wanted_total >= layout_total(analysis, units, hi):
        return hi
    for _ in range(60):
        mid = (lo + hi) / 2
        if layout_total(analysis, units, mid) < wanted_total:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
