import json
import os
from pathlib import Path

import pytest

from narrareel import config
from narrareel.captions import colors
from narrareel.captions import fonts as fonts_mod
from narrareel.captions.ass import ass_time, build_captions, escape_text
from narrareel.captions.chunk import (
    CapWord,
    auto_emphasis,
    build_cap_words,
    chunk_words,
    display_text,
    fit_lines,
)
from narrareel.captions.formats import FormatError, get_format, list_formats
from narrareel.captions.styles import (
    StyleError,
    get_style,
    json_schema,
    list_styles,
    resolve_style,
    save_user_style,
)
from narrareel.errors import NarraReelError
from narrareel.script import analyze_script
from narrareel.timing.estimate import estimate_script_timings

GOLDEN = Path(__file__).parent.parent / "golden"
SCRIPT = "Wake up early. Grind hard, every single day! In 2026 nobody is coming to save you."


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path / "home"))


# ------------------------------------------------------------------- colours


def test_ass_colour_is_bgr_with_inverted_alpha():
    assert colors.ass_style_color("#FFE600") == "&H0000E6FF"  # the example from the spec
    assert colors.ass_style_color("#FF0000") == "&H000000FF"  # red -> BGR
    assert colors.ass_style_color("#000000AA") == "&H55000000"  # 0xAA opaque -> 0x55 transparent
    assert colors.ass_style_color("#fff") == "&H00FFFFFF"
    assert colors.ass_tag_color("#112233") == "&H332211&"
    assert colors.ass_tag_alpha("#00000000") == "&HFF&"
    assert colors.ass_tag_alpha("#000000") == "&H00&"


@pytest.mark.parametrize("bad", ["red", "#12", "#GGGGGG", "", "#1234567"])
def test_bad_colours(bad):
    with pytest.raises(NarraReelError):
        colors.parse_hex(bad)


# -------------------------------------------------------------------- styles


def test_nine_presets_validate_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((config.presets_dir() / "styles" / "schema.json").read_text(encoding="utf-8"))
    assert schema == json_schema(), "schema.json is stale: run scripts/write_presets.py"
    ids = []
    for path in sorted((config.presets_dir() / "styles").glob("*.json")):
        if path.name == "schema.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.validate(data, schema)
        ids.append(data["id"])
    assert sorted(ids) == sorted(
        ["bold-pop", "karaoke", "boxed", "one-word", "minimal", "neon", "keyword-emphasis",
         "subtitle-classic", "typewriter"]
    )


def test_every_preset_uses_a_bundled_font_and_loads():
    for s in list_styles():
        assert fonts_mod.get_font(s.font.id).path.is_file()
        assert get_style(s.id).id == s.id


def test_resolve_style_overrides_and_font():
    s = resolve_style("bold-pop", {"colors": {"highlight": "#FF4B4B"}, "layout": {"words_per_chunk": 2}},
                      font="anton-regular")
    assert s.colors.highlight == "#FF4B4B" and s.colors.text == "#FFFFFF"
    assert s.layout.words_per_chunk == 2 and s.font.id == "anton-regular"
    assert get_style("bold-pop").colors.highlight == "#FFE600"  # presets are never mutated


def test_invalid_style_input():
    with pytest.raises(StyleError, match="Unknown caption style"):
        get_style("nope")
    with pytest.raises(StyleError, match="Invalid caption settings"):
        resolve_style("bold-pop", {"layout": {"words_per_chunk": 99}})
    with pytest.raises(StyleError):
        resolve_style("bold-pop", {"colors": {"text": "blue"}})


def test_user_presets_roundtrip():
    style = resolve_style("bold-pop", {"colors": {"highlight": "#00FF00"}})
    style = style.model_copy(update={"name": "Bold Pop"})
    path = save_user_style(style)
    assert path.name == "my-bold-pop.json"
    saved = get_style("my-bold-pop")
    assert saved.colors.highlight == "#00FF00"
    assert "my-bold-pop" in [s.id for s in list_styles()]


# ------------------------------------------------------------------- formats


def test_formats():
    ids = {f.id for f in list_formats()}
    assert ids == {"reels", "youtube", "square", "portrait", "audio"}
    reels = get_format("reels")
    assert (reels.width, reels.height) == (1080, 1920) and reels.is_video
    assert reels.position_y("lower_middle") == round(1920 * 0.62)
    assert reels.position_y("middle", 30) == 960 + 30
    assert not get_format("audio").is_video
    with pytest.raises(FormatError):
        get_format("tiktok2")
    with pytest.raises(FormatError):
        get_format("audio").position_y("middle")


# --------------------------------------------------------------------- fonts


def test_bundled_fonts_manifest_is_complete_and_licensed():
    fonts = fonts_mod.list_fonts()
    assert len(fonts) >= 15
    for f in fonts:
        assert f.path.is_file(), f.id
        assert f.license in ("OFL-1.1", "Apache-2.0"), f.id
        assert f.license_file and f.license_file.is_file(), f.id
        family, _, weight = fonts_mod.read_font_names(f.path)
        assert family == f.ass_family
    total = sum(f.path.stat().st_size for f in fonts)
    assert total < 15 * 1024 * 1024
    assert {"bold", "clean", "fun", "handwritten", "multilingual"} <= {t for f in fonts for t in f.tags}


def test_font_lookup_and_unknown():
    assert fonts_mod.get_font("montserrat-black").ass_family == "Montserrat Black"
    assert fonts_mod.get_font("poppins-bold").ass_bold is True
    with pytest.raises(fonts_mod.FontError, match="Unknown font"):
        fonts_mod.get_font("comic-sans")
    assert fonts_mod.list_fonts("handwritten")[0].family == "Permanent Marker"


def test_glyph_coverage_for_hindi():
    montserrat = fonts_mod.get_font("montserrat-black")
    noto = fonts_mod.get_font("noto-sans-devanagari-bold")
    assert fonts_mod.missing_glyphs(montserrat, "Hello") == set()
    assert fonts_mod.missing_glyphs(montserrat, "नमस्ते")
    assert fonts_mod.missing_glyphs(noto, "नमस्ते") == set()


def test_font_preview_png_is_cached():
    f = fonts_mod.get_font("anton-regular")
    a = fonts_mod.preview_png(f)
    assert a[:8] == b"\x89PNG\r\n\x1a\n"
    assert fonts_mod.preview_png(f) == a


def test_user_font_upload_validates_by_decoding():
    src = fonts_mod.get_font("lilita-one-regular").path
    info = fonts_mod.add_user_font(src.read_bytes(), "My Font.ttf")
    assert info.user and info.id.startswith("user-") and info.ass_family == "Lilita One"
    assert info.id in [f.id for f in fonts_mod.list_fonts()]
    with pytest.raises(fonts_mod.FontError, match="could not be loaded"):
        fonts_mod.add_user_font(b"not a font at all", "fake.ttf")
    with pytest.raises(fonts_mod.FontError, match="Only .ttf and .otf"):
        fonts_mod.add_user_font(b"x", "evil.exe")


def test_measure_font_matches_ass_size_convention():
    f = fonts_mod.get_font("montserrat-black")
    pil = fonts_mod.measure_font(f, 100)
    asc, desc = pil.getmetrics()
    assert asc + desc == pytest.approx(100, abs=2)  # libass sizes by ascent+descent


def test_copy_fonts_for_job(tmp_path):
    f = fonts_mod.get_font("anton-regular")
    d = fonts_mod.copy_fonts_for_job([f, f], tmp_path / "fonts")
    assert [p.name for p in d.iterdir()] == [f.path.name]


# -------------------------------------------------------------------- chunks


def test_display_text_strips_emoji_and_uppercases():
    assert display_text("Great 🎉", True) == "GREAT"
    assert display_text("Great 🎉", False, keep_emoji=True) == "Great 🎉"
    assert display_text("a   b", False) == "a b"


def test_auto_emphasis():
    assert auto_emphasis("2026") and auto_emphasis("incredible") and auto_emphasis("NASA")
    assert not auto_emphasis("it") and not auto_emphasis("The")


def test_fit_lines():
    assert fit_lines([100, 100, 100], 10, 400, 2) == [[0, 1, 2]]
    assert fit_lines([100, 100, 100, 100], 10, 250, 2) == [[0, 1], [2, 3]]
    assert fit_lines([100, 100, 100, 100], 10, 250, 1) is None
    assert fit_lines([300, 300], 10, 250, 2) is None
    assert fit_lines([], 10, 100, 2) == []


def cw(text, start, end, sentence=0):
    return CapWord(text, start, end, sentence)


def width(w):
    return 10.0 * len(w.text)


def test_chunking_basic_rules():
    style = resolve_style("bold-pop", {"layout": {"words_per_chunk": 3}})
    words = [cw("one", 0.0, 0.3), cw("two", 0.3, 0.6), cw("three", 0.6, 1.0), cw("four", 1.0, 1.3),
             cw("five.", 1.3, 1.7), cw("Next", 2.5, 2.8, 1), cw("sentence", 2.8, 3.2, 1)]
    chunks = chunk_words(words, style, width, 5.0, 10_000)
    texts = [[w.text for w in c.words] for c in chunks]
    assert texts == [["one", "two", "three"], ["four", "five."], ["Next", "sentence"]]
    assert chunks[0].start == 0.0 and chunks[0].end == pytest.approx(1.0)  # next starts at 1.0
    assert chunks[1].end == pytest.approx(1.7 + 0.15)  # hold, next chunk starts later
    for a, b in zip(chunks, chunks[1:], strict=False):
        assert a.end <= b.start + 1e-9


def test_chunking_breaks_on_pause_and_punctuation():
    style = resolve_style("bold-pop", {"layout": {"words_per_chunk": 6}})
    words = [cw("Hello", 0, 0.3), cw("there,", 0.3, 0.6), cw("my", 0.6, 0.8), cw("friend", 0.8, 1.1),
             cw("wait", 1.6, 1.9)]
    chunks = chunk_words(words, style, width, 5.0, 10_000)
    assert [[w.text for w in c.words] for c in chunks] == [["Hello", "there,"], ["my", "friend"],
                                                           ["wait"]]


def test_chunking_one_word_mode():
    style = resolve_style("one-word")
    words = [cw("A", 0, 0.2), cw("big", 0.2, 0.4), cw("moment", 0.4, 0.8)]
    chunks = chunk_words(words, style, width, 5.0, 10_000)
    assert [len(c.words) for c in chunks] == [1, 1, 1]
    assert all(c.end - c.start >= 0.4 - 1e-9 or c is chunks[-1] or c.end == chunks[chunks.index(c) + 1].start
               for c in chunks)


def test_chunking_respects_width_and_lines():
    style = resolve_style("bold-pop", {"layout": {"words_per_chunk": 8, "max_lines": 2}})
    words = [cw("aaaaaaaa", i * 0.3, i * 0.3 + 0.25) for i in range(8)]  # 80 px each
    chunks = chunk_words(words, style, width, 10.0, 200)  # only two words per line fit
    for c in chunks:
        assert len(c.lines) <= 2
        for line in c.lines:
            assert sum(width(c.words[i]) for i in line) + 10 * (len(line) - 1) <= 200
    assert sum(len(c.words) for c in chunks) == 8


def test_orphan_short_word_joins_neighbour():
    style = resolve_style("bold-pop", {"layout": {"words_per_chunk": 3}})
    words = [cw("alpha", 0, 0.3), cw("beta", 0.3, 0.6), cw("gamma", 0.6, 0.9), cw("up.", 0.9, 1.1)]
    chunks = chunk_words(words, style, width, 5.0, 10_000)
    assert [[w.text for w in c.words] for c in chunks] == [["alpha", "beta", "gamma", "up."]]


def test_cap_words_drop_pure_emoji_and_flag_emphasis():
    a = analyze_script("This is *big* news 🎉 today.")
    words, _ = estimate_script_timings(a)
    style = resolve_style("keyword-emphasis")
    caps = build_cap_words(words, a, style)
    assert [w.text for w in caps] == ["This", "is", "big", "news", "today."]
    assert [w.text for w in caps if w.emphasis] == ["big"]
    plain = build_cap_words(words, a, resolve_style("bold-pop"))
    assert not any(w.emphasis for w in plain)


# ----------------------------------------------------------------------- ass


def test_ass_time_and_escape():
    assert ass_time(3723.456) == "1:02:03.46"
    assert ass_time(0.0) == "0:00:00.00"
    assert escape_text("a{b}\\c\nd") == "abc d"


def _build(preset, script=SCRIPT, fmt="reels", **overrides):
    a = analyze_script(script)
    words, _ = estimate_script_timings(a)
    style = resolve_style(preset, overrides or None)
    return build_captions(words, a, style, get_format(fmt))


def test_ass_structure_and_style_line():
    res = _build("bold-pop")
    lines = res.ass.splitlines()
    assert "PlayResX: 1080" in lines and "PlayResY: 1920" in lines and "WrapStyle: 2" in lines
    style = next(ln for ln in lines if ln.startswith("Style: Main"))
    fields = style.split(",")
    assert fields[1] == "Montserrat Black" and fields[2] == "100"
    assert fields[3] == "&H00FFFFFF" and fields[4] == "&H0000E6FF"  # text, highlight
    assert fields[5] == "&H00000000" and fields[6] == "&H55000000"  # outline, shadow
    assert fields[7] == "0"  # not bold: the weight is in the family name
    events = [ln for ln in lines if ln.startswith("Dialogue:")]
    assert len(events) == analyze_script(SCRIPT).word_count  # one event per spoken word
    assert "\\an5\\pos(540,1190)" in events[0]
    assert "\\t(0,120,\\fscx100\\fscy100)" in events[0]  # pop-in on the first event
    assert "\\t(" not in events[1]  # ...and only the first


def _first_event(res):
    return next(ln for ln in res.ass.splitlines() if ln.startswith("Dialogue:"))


def test_text_can_be_placed_left_or_right_and_nudged():
    reels = get_format("reels")  # 1080 wide, 8 % side margins, 10 % button column on the right
    left = _build("bold-pop", layout={"align_x": "left"})
    assert "\\an4\\pos(86,1190)" in _first_event(left)
    right = _build("bold-pop", layout={"align_x": "right"})
    assert "\\an6\\pos(972,1190)" in _first_event(right)  # clear of the button column
    nudged = _build("bold-pop", layout={"align_x": "center", "offset_x": -100, "offset_y": 50})
    assert "\\an5\\pos(440,1240)" in _first_event(nudged)
    x, an, room = reels.anchor_x("right")
    assert (x, an) == (972, 6) and room == pytest.approx(972 - 86.4)


def test_side_aligned_text_wraps_inside_the_room_it_has():
    x, _, room = get_format("reels").anchor_x("left")
    res = _build("minimal", script="word " * 40, layout={"align_x": "left", "words_per_chunk": 8})
    assert x == 86 and room < 1080  # the room shrinks to the margins, so chunks are budgeted for it
    assert res.chunks


def test_active_word_is_highlighted_in_each_event():
    res = _build("bold-pop")
    events = [ln for ln in res.ass.splitlines() if ln.startswith("Dialogue:")]
    yellow = colors.ass_tag_color("#FFE600")
    for ev in events:
        assert ev.count(f"\\c{yellow}") == 1


def test_bold_flag_for_static_bold_fonts():
    res = _build("boxed")  # Poppins Bold is a static "Bold" face: family + Bold flag
    style = next(ln for ln in res.ass.splitlines() if ln.startswith("Style: Main"))
    assert style.split(",")[1] == "Poppins" and style.split(",")[7] == "-1"


def test_box_highlight_uses_border_tags():
    res = _build("boxed")
    ev = next(ln for ln in res.ass.splitlines() if ln.startswith("Dialogue:"))
    assert "\\3c&H6B3BFF&" in ev and "\\bord9" in ev  # #FF3B6B as BGR
    assert "\\bord0" in ev  # inactive words have no outline


def test_subtitle_classic_uses_opaque_box_border_style():
    res = _build("subtitle-classic", fmt="youtube")
    lines = res.ass.splitlines()
    style = next(ln for ln in lines if ln.startswith("Style: Main")).split(",")
    assert style[15] == "3" and style[5] == "&H4C000000"  # BorderStyle 3, box colour w/ alpha
    assert "PlayResX: 1920" in lines
    events = [ln for ln in lines if ln.startswith("Dialogue:")]
    assert all("\\3a&H4C&" in e for e in events)  # box alpha survives the per-word tags
    assert all("\\pos(960,961)" in e for e in events[:1])  # bottom = 89% of 1080


def test_mode_none_has_one_event_per_chunk():
    res = _build("minimal")
    events = [ln for ln in res.ass.splitlines() if ln.startswith("Dialogue:")]
    assert len(events) == len(res.chunks)


def test_fade_and_blur_tags():
    res = _build("neon")
    events = [ln for ln in res.ass.splitlines() if ln.startswith("Dialogue:")]
    assert "\\blur3" in events[0] and "\\fad(120,0)" in events[0]
    # the last event of a chunk fades out
    assert any("\\fad(0,60)" in e or "\\fad(120,60)" in e for e in events)


def test_events_are_contiguous_within_a_chunk():
    res = _build("bold-pop")
    events = [ln for ln in res.ass.splitlines() if ln.startswith("Dialogue:")]
    parsed = [(e.split(",")[1], e.split(",")[2]) for e in events]
    for (s1, e1), (s2, _e2) in zip(parsed, parsed[1:], strict=False):
        assert s2 >= s1  # events never go back in time
        assert e1 <= s2 or s2 == s1 or e1 > s1  # and none is empty


def test_keyword_emphasis_scales_words():
    res = _build("keyword-emphasis")
    assert "\\fscx130\\fscy130" in res.ass and "2026" in res.ass


def test_missing_glyph_warning_for_hindi_with_latin_font():
    res = _build("bold-pop", script="नमस्ते दुनिया।")
    assert any("can't show these characters" in w and "Noto Sans Devanagari" in w
               for w in res.warnings)


def test_hindi_with_devanagari_font_has_no_warning():
    a = analyze_script("नमस्ते दुनिया।")
    words, _ = estimate_script_timings(a)
    style = resolve_style("bold-pop", font="noto-sans-devanagari-bold",
                          overrides={"font": {"uppercase": False}})
    res = build_captions(words, a, style, get_format("reels"))
    assert res.warnings == []


@pytest.mark.parametrize("preset", [s.id for s in list_styles()])
def test_golden_ass_per_preset(preset):
    script = "Wake up early. Grind hard every day, because 2026 is yours!"
    res = _build(preset, script=script, fmt="youtube" if preset == "subtitle-classic" else "reels")
    golden = GOLDEN / f"{preset}.ass"
    if os.environ.get("UPDATE_GOLDEN"):
        golden.parent.mkdir(exist_ok=True)
        golden.write_text(res.ass, encoding="utf-8", newline="\n")
    assert golden.is_file(), "run with UPDATE_GOLDEN=1 to create golden files"
    assert res.ass == golden.read_text(encoding="utf-8")
