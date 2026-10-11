"""Script analysis: normalise, split into sentences and words, count, warn.

Pure Python, no network, no ML. See WHAT_TO_DO.md section 5.1.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..models import ScriptAnalysis, ScriptWarning, Sentence, Token

TERMINATORS = ".!?…।॥"
_TERM_RUN = re.compile(r"[.!?…।॥]+[\"'”’)\]]*(?=\s|$)")
_EMPHASIS = re.compile(r"\*(?=\S)([^*\n]*?\S)\*")
_URL = re.compile(r"(https?://|www\.)\S+|\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.IGNORECASE)

# Never end a sentence after these.
_NEVER_SPLIT = {"mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "vs.", "e.g.", "i.e.", "u.s.", "u.k."}
# End a sentence after these only when the next word is capitalised.
_SPLIT_IF_CAPITAL = {"etc.", "a.m.", "p.m."}

SYMBOLS = set("$%&@#→+=<>^~|\\€£¥₹©®™")

LONG_SENTENCE_WORDS = 35
SPLIT_FOR_SYNTH_WORDS = 60
VERY_LONG_SCRIPT_WORDS = 3000


# ------------------------------------------------------------------ helpers


def normalize_text(text: str) -> str:
    """NFC, LF line endings, collapsed spaces, at most one blank line between paragraphs."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace(" ", " ").replace("​", "").replace("﻿", "")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")


def _is_wordlike(token: str) -> bool:
    return any(ch.isalnum() for ch in token)


def fold(token: str) -> str:
    """Lower-case, strip punctuation, drop accents from Latin letters (keeps Devanagari marks)."""
    out: list[str] = []
    for ch in unicodedata.normalize("NFKD", token):
        if unicodedata.combining(ch):
            if out and out[-1].isascii():
                continue  # accent on a Latin letter
            out.append(ch)
        elif ch.isalnum():
            out.append(ch.lower())
        elif unicodedata.category(ch) in ("Mn", "Mc"):
            out.append(ch)
    return "".join(out)


def _is_emoji(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x1F300 <= cp <= 0x1FAFF
        or 0x2600 <= cp <= 0x27BF
        or 0x1F000 <= cp <= 0x1F2FF
        or cp in (0x2B50, 0x2B55, 0x231A, 0x231B, 0x203C, 0x2049)
    )


def _script_counts(text: str) -> tuple[int, int]:
    devanagari = latin = 0
    for ch in text:
        if "ऀ" <= ch <= "ॿ":
            if ch.isalpha():
                devanagari += 1
        elif ch.isalpha() and (ch.isascii() or "À" <= ch <= "ɏ"):
            latin += 1
    return devanagari, latin


def detect_language(text: str) -> str:
    devanagari, latin = _script_counts(text)
    if devanagari + latin == 0:
        return "unknown"
    return "hi" if devanagari > latin else "en"


def _strip_emphasis(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Remove ``*word*`` markers; return clean text and emphasis spans in clean coordinates."""
    spans: list[tuple[int, int]] = []
    out: list[str] = []
    last = 0
    length = 0
    for m in _EMPHASIS.finditer(text):
        out.append(text[last : m.start()])
        length += m.start() - last
        inner = m.group(1)
        spans.append((length, length + len(inner)))
        out.append(inner)
        length += len(inner)
        last = m.end()
    out.append(text[last:])
    return "".join(out), spans


# --------------------------------------------------------- sentence splitting


def _split_line(line: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of sentences inside one line."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _TERM_RUN.finditer(line):
        end = m.end()
        run = m.group()
        core = run.rstrip("\"'”’)]")
        rest = line[end:].lstrip()
        # Quotes do not determine capitalization: look at the text inside them,
        # including nested quotes, without changing the original sentence spans.
        nxt = rest.lstrip("\"'“‘")[:1]
        ws = max(line.rfind(" ", 0, m.start()), -1)
        word = line[ws + 1 : end].lstrip("\"'“‘([")
        word_l = word.lower().rstrip("\"'”’)]")

        if "…" in core or core.endswith("..") or len(core) >= 2 and set(core) == {"."}:
            if nxt and nxt.islower():
                continue
        elif core == ".":
            if word_l in _NEVER_SPLIT:
                continue
            if word_l in _SPLIT_IF_CAPITAL and not (nxt and nxt.isupper()):
                continue
            if re.fullmatch(r"[A-Z]\.", word.rstrip("\"'”’)]")) and nxt and nxt.isupper():
                continue  # initials: "J. K. Rowling"
            if re.fullmatch(r"\d+\.", word_l) and line[start:ws + 1].strip() == "" and nxt:
                continue  # list marker: "1. First"
        spans.append((start, end))
        start = end
        while start < len(line) and line[start] == " ":
            start += 1
    if start < len(line) and line[start:].strip():
        spans.append((start, len(line)))
    return spans


def _ends_with_terminator(text: str) -> bool:
    return text.rstrip("\"'”’)]").endswith(tuple(TERMINATORS))


@dataclass
class _Seg:
    start: int
    end: int
    para: int


def _segments(text: str) -> list[_Seg]:
    segs: list[_Seg] = []
    offset = 0
    para = -1
    new_para = True
    for line in text.split("\n"):
        base = offset
        offset += len(line) + 1
        if not line.strip():
            new_para = True
            continue
        if new_para:
            para += 1
            new_para = False
        for s, e in _split_line(line):
            segs.append(_Seg(base + s, base + e, para))
    return segs


def _merge_fragments(text: str, segs: list[_Seg]) -> list[_Seg]:
    merged: list[_Seg] = []
    for seg in segs:
        body = text[seg.start : seg.end]
        words = [w for w in body.split() if _is_wordlike(w)]
        if (
            merged
            and merged[-1].para == seg.para
            and len(words) < 2
            and not _ends_with_terminator(body)
        ):
            merged[-1].end = seg.end
        else:
            merged.append(_Seg(seg.start, seg.end, seg.para))
    return merged


# ------------------------------------------------------------------- main API


def analyze_script(raw: str) -> ScriptAnalysis:
    """Analyse a script. An empty script yields an empty analysis (callers decide how to react)."""
    text = normalize_text(raw)
    text, emphasis_spans = _strip_emphasis(text)

    segs = _merge_fragments(text, _segments(text))
    tokens: list[Token] = []
    sentences: list[Sentence] = []
    warnings: list[ScriptWarning] = []

    for seg in segs:
        sidx = len(sentences)
        t_start = len(tokens)
        pending_prefix = ""
        for m in re.finditer(r"\S+", text[seg.start : seg.end]):
            s = seg.start + m.start()
            e = seg.start + m.end()
            raw_tok = m.group()
            if not _is_wordlike(raw_tok):
                # Pure punctuation / emoji: attach to the previous word for display.
                if len(tokens) > t_start:
                    prev = tokens[-1]
                    tokens[-1] = prev.model_copy(update={"text": f"{prev.text} {raw_tok}", "end_char": e})
                else:
                    pending_prefix = f"{pending_prefix}{raw_tok} "
                continue
            tok_text = pending_prefix + raw_tok
            pending_prefix = ""
            emphasis = any(a <= s < b for a, b in emphasis_spans)
            tokens.append(
                Token(
                    text=tok_text,
                    norm=fold(raw_tok),
                    start_char=s,
                    end_char=e,
                    sentence_idx=sidx,
                    emphasis=emphasis,
                )
            )
        if len(tokens) == t_start:
            continue  # nothing speakable in this segment (e.g. only "...")
        sentences.append(
            Sentence(
                idx=sidx,
                text=text[seg.start : seg.end].replace("\n", " ").strip(),
                paragraph_idx=seg.para,
                token_start=t_start,
                token_end=len(tokens),
            )
        )
        # keep paragraph indices dense and mark paragraph ends
    # Re-number paragraphs densely (a paragraph of only punctuation could have been skipped)
    para_ids = sorted({s.paragraph_idx for s in sentences})
    remap = {old: new for new, old in enumerate(para_ids)}
    for i, s in enumerate(sentences):
        s.paragraph_idx = remap[s.paragraph_idx]
        nxt = sentences[i + 1] if i + 1 < len(sentences) else None
        s.ends_paragraph = nxt is None or remap[nxt.paragraph_idx] != s.paragraph_idx

    word_count = len(tokens)
    char_count = sum(
        1
        for t in tokens
        for ch in t.text
        if ch.isalnum() or unicodedata.category(ch) in ("Mn", "Mc")
    )
    analysis = ScriptAnalysis(
        text=text,
        language_hint=detect_language(text),
        tokens=tokens,
        sentences=sentences,
        word_count=word_count,
        char_count=char_count,
        paragraph_count=len(para_ids),
        warnings=warnings,
    )
    analysis.warnings.extend(_collect_warnings(analysis))
    return analysis


def _collect_warnings(a: ScriptAnalysis) -> list[ScriptWarning]:
    out: list[ScriptWarning] = []
    for s in a.sentences:
        n = s.token_end - s.token_start
        if n > LONG_SENTENCE_WORDS:
            out.append(
                ScriptWarning(
                    code="long_sentence",
                    sentence_idx=s.idx,
                    message=(
                        f"Sentence {s.idx + 1} has {n} words. Long sentences sound rushed and make "
                        "captions harder to read. Consider splitting it."
                    ),
                )
            )
    text = a.text
    if any(ch.isdigit() for ch in text):
        out.append(
            ScriptWarning(
                code="contains_numbers",
                message="Numbers may be read differently than you expect. Preview the voice to check.",
            )
        )
    if _URL.search(text):
        out.append(
            ScriptWarning(
                code="contains_url_or_email",
                message="URLs and email addresses are read out letter by letter. Consider spelling them out.",
            )
        )
    if any(ch in SYMBOLS for ch in text):
        out.append(
            ScriptWarning(
                code="contains_symbols",
                message="Symbols like $ % & @ may be read oddly. Preview the voice to check.",
            )
        )
    if any(_is_emoji(ch) for ch in text):
        out.append(
            ScriptWarning(
                code="contains_emoji",
                message="Emoji are usually skipped by voices and may not render in captions.",
            )
        )
    if a.word_count > VERY_LONG_SCRIPT_WORDS:
        out.append(
            ScriptWarning(
                code="very_long_script",
                message=f"{a.word_count} words is a long script. Generation may take a while.",
            )
        )
    devanagari, latin = _script_counts(text)
    if devanagari and latin:
        out.append(
            ScriptWarning(
                code="mixed_scripts",
                message="Your script mixes Hindi (Devanagari) and Latin text. Pick a voice and font that cover both.",
            )
        )
    return out


# ----------------------------------------------------------- synthesis units


@dataclass(frozen=True)
class SynthUnit:
    """A piece of text sent to a TTS engine in one call (a sentence or part of a long one)."""

    sentence_idx: int
    token_start: int
    token_end: int  # exclusive
    text: str


_BREAK_ENDINGS = (";", ":", "—", ",", "–")


def _best_split(tokens: list[Token], lo: int, hi: int) -> int:
    """Index in (lo, hi) at which to split so both halves stay balanced; prefers punctuation."""
    mid = (lo + hi) // 2
    best = None
    best_dist = None
    for i in range(lo + 1, hi):
        prev = tokens[i - 1].text.rstrip()
        if prev.endswith(_BREAK_ENDINGS):
            dist = abs(i - mid)
            if best_dist is None or dist < best_dist:
                best, best_dist = i, dist
    return best if best is not None else mid


def _split_range(tokens: list[Token], lo: int, hi: int, limit: int) -> list[tuple[int, int]]:
    if hi - lo <= limit:
        return [(lo, hi)]
    cut = _best_split(tokens, lo, hi)
    return _split_range(tokens, lo, cut, limit) + _split_range(tokens, cut, hi, limit)


def synthesis_units(analysis: ScriptAnalysis, limit: int = SPLIT_FOR_SYNTH_WORDS) -> list[SynthUnit]:
    """Sentences, with those longer than ``limit`` words cut at the best punctuation near the middle."""
    units: list[SynthUnit] = []
    for s in analysis.sentences:
        for lo, hi in _split_range(analysis.tokens, s.token_start, s.token_end, limit):
            text = " ".join(t.text for t in analysis.tokens[lo:hi])
            units.append(SynthUnit(s.idx, lo, hi, text))
    return units
