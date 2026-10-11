import pytest

from narrareel.errors import ScriptError
from narrareel.models import ScriptAnalysis, Sentence
from narrareel.script import analyze_script, format_duration, parse_duration, plan, speed_quality
from narrareel.script import duration as d


def synthetic(words=742, chars=4100, sentences=38, paragraphs=6) -> ScriptAnalysis:
    """The worked example from WHAT_TO_DO.md 5.2.3: 38 sentences in 6 paragraphs."""
    per_para = [sentences // paragraphs + (1 if i < sentences % paragraphs else 0)
                for i in range(paragraphs)]
    sents, idx = [], 0
    for p, n in enumerate(per_para):
        for j in range(n):
            sents.append(Sentence(idx=idx, text="x", paragraph_idx=p, token_start=0, token_end=0,
                                  ends_paragraph=(j == n - 1)))
            idx += 1
    return ScriptAnalysis(text="x", tokens=[], sentences=sents, word_count=words,
                          char_count=chars, paragraph_count=paragraphs)


@pytest.mark.parametrize("text,expected", [
    ("6m", 360), ("6:00", 360), ("1:02:00", 3720), ("90s", 90), ("90", 90),
    ("1m30s", 90), ("1.5m", 90), ("2h", 7200), ("1 m 30 s", 90), ("45 sec", 45),
])
def test_parse_duration(text, expected):
    assert parse_duration(text) == pytest.approx(expected)


@pytest.mark.parametrize("bad", ["", "abc", "0", "1:2:3:4", "5x", "m"])
def test_parse_duration_invalid(bad):
    with pytest.raises(ScriptError):
        parse_duration(bad)


def test_format_duration():
    assert format_duration(308.7) == "5:09"
    assert format_duration(59.4) == "0:59"
    assert format_duration(3723) == "1:02:03"


def test_speed_quality_zones():
    assert speed_quality(1.0) == "natural"
    assert speed_quality(0.90) == "natural"
    assert speed_quality(1.15) == "natural"
    assert speed_quality(0.85) == "noticeable"
    assert speed_quality(1.26) == "noticeable"
    assert speed_quality(0.75) == "strong"
    assert speed_quality(1.31) == "strong"
    assert speed_quality(0.6) == "not_recommended"
    assert speed_quality(1.8) == "not_recommended"


def test_pause_extremes_match_spec():
    a = synthetic()
    assert d.pause_seconds(a, 1.0) == pytest.approx(15.85)
    assert d.pause_seconds(a, d.SCALE_MAX) == pytest.approx(42.5)
    assert d.pause_seconds(a, d.SCALE_MIN) == pytest.approx(7.1)


def test_estimate_default():
    a = synthetic()
    est = d.estimate(a, cps=14.0)
    assert est.speech_seconds == pytest.approx(292.857, abs=0.01)
    assert est.total_seconds == pytest.approx(308.71, abs=0.01)


def test_plan_longer_target_worked_example():
    p = plan(synthetic(), cps=14.0, target_seconds=360)
    a, b, c = p.options
    assert (a.kind, b.kind, c.kind) == ("edit_script", "adjust_delivery", "speed_only")
    assert a.words_delta == pytest.approx(123, abs=1)
    assert b.speed == pytest.approx(0.92, abs=0.01)
    assert b.pause_scale == pytest.approx(d.SCALE_MAX)
    assert b.quality == "natural"
    assert c.speed == pytest.approx(0.85, abs=0.01)
    assert c.quality == "noticeable"
    assert b.resulting_seconds == pytest.approx(360, abs=0.5)
    assert p.recommended == 1


def test_plan_shorter_target_worked_example():
    p = plan(synthetic(), cps=14.0, target_seconds=240)
    a, b, c = p.options
    assert a.words_delta == pytest.approx(-165, abs=1)
    assert b.speed == pytest.approx(1.26, abs=0.01)
    assert b.quality == "noticeable"
    assert c.speed == pytest.approx(1.31, abs=0.01)
    assert c.quality == "strong"
    assert p.recommended == 1


def test_plan_small_gap_prefers_pauses_only():
    a = synthetic()
    est = d.estimate(a, cps=14.0).total_seconds
    p = plan(a, cps=14.0, target_seconds=est + 10)
    b = next(o for o in p.options if o.kind == "adjust_delivery")
    assert b.speed == 1.0
    assert b.pause_scale > 1.0
    assert b.resulting_seconds == pytest.approx(est + 10, abs=0.05)


def test_plan_target_close_to_estimate_has_no_edit_option():
    a = synthetic()
    est = d.estimate(a, cps=14.0).total_seconds
    p = plan(a, cps=14.0, target_seconds=est * 1.01)
    assert [o.kind for o in p.options] == ["adjust_delivery", "speed_only"]
    assert p.recommended == 0


def test_plan_impossible_target():
    p = plan(synthetic(), cps=14.0, target_seconds=5)
    a, b, c = p.options
    assert a.words_delta < -600
    assert b.quality == "not_recommended" and c.quality == "not_recommended"
    assert "Cut about" in b.message
    assert p.recommended == 0


def test_plan_without_target_lists_preset_speeds():
    p = plan(synthetic(), cps=14.0)
    assert [o.speed for o in p.options] == [0.75, 1.0, 1.25, 1.5, 2.0]
    assert p.options[p.recommended].speed == 1.0
    assert p.options[1].resulting_seconds == pytest.approx(308.71, abs=0.01)


def test_plan_one_sentence_script():
    a = analyze_script("Just one short sentence here.")
    p = plan(a, cps=14.0, target_seconds=10)
    assert len(p.options) >= 2
    assert all(o.resulting_seconds > 0 for o in p.options)


def test_default_cps_per_language():
    assert d.default_cps("en") == 14.0
    assert d.default_cps("hi") == 12.0
    assert d.default_cps("ta") == 11.8
    assert d.default_cps("unknown") == d.FALLBACK_CPS


def test_tamil_script_gets_the_tamil_rate(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path))
    a = analyze_script("வணக்கம் உலகம். இது ஒரு சோதனை.")
    assert d.get_cps("edge:x", a.language_hint) == (11.8, "default")


def test_calibration_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRAREEL_HOME", str(tmp_path))
    assert d.get_cps("edge:x", "en") == (14.0, "default")
    d.update_calibration("edge:x", chars=1500, speech_seconds=100, speed=1.0)
    assert d.get_cps("edge:x", "en") == (pytest.approx(15.0), "calibrated")
    d.update_calibration("edge:x", chars=1700, speech_seconds=100, speed=1.0)
    cps, _ = d.get_cps("edge:x")
    assert cps == pytest.approx(16.0)
    # speed is factored out
    d.update_calibration("edge:y", chars=3000, speech_seconds=100, speed=2.0)
    assert d.get_cps("edge:y")[0] == pytest.approx(15.0)
