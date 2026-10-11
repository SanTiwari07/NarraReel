import time

import pytest

from narrareel.script import analyze_script, synthesis_units


def test_abbreviations_and_decimals():
    a = analyze_script("Hello world. This is Dr. Smith! Is it 3.5 now?")
    assert len(a.sentences) == 3
    assert a.sentences[1].text == "This is Dr. Smith!"


def test_line_break_is_sentence_break():
    a = analyze_script("Line one\nLine two")
    assert len(a.sentences) == 2


def test_paragraphs():
    a = analyze_script("Para one.\n\nPara two.")
    assert len(a.sentences) == 2
    assert a.paragraph_count == 2
    assert a.sentences[0].ends_paragraph and a.sentences[1].ends_paragraph
    assert a.sentences[0].paragraph_idx == 0 and a.sentences[1].paragraph_idx == 1


def test_same_paragraph_not_ends_paragraph():
    a = analyze_script("One. Two. Three.")
    assert [s.ends_paragraph for s in a.sentences] == [False, False, True]


def test_hindi():
    a = analyze_script("नमस्ते दुनिया। यह एक परीक्षण है।")
    assert len(a.sentences) == 2
    assert a.language_hint == "hi"
    assert a.word_count == 6


def test_dash_attaches_to_previous_word():
    a = analyze_script("Wait — what?!")
    assert a.word_count == 2
    assert a.tokens[0].text == "Wait —"
    assert a.tokens[1].text == "what?!"


def test_empty_script():
    a = analyze_script("   \n\n  ")
    assert a.word_count == 0 and a.sentences == [] and a.tokens == []
    assert a.language_hint == "unknown"


def test_initials_and_titles_do_not_split():
    a = analyze_script("J. K. Rowling wrote it. Mr. Brown read it.")
    assert len(a.sentences) == 2


def test_ellipsis_inside_sentence():
    a = analyze_script("Well... maybe not. Okay.")
    assert [s.text for s in a.sentences] == ["Well... maybe not.", "Okay."]


def test_ellipsis_before_capital_splits():
    a = analyze_script("I waited... Then it came.")
    assert len(a.sentences) == 2


@pytest.mark.parametrize("opening,closing", [('"', '"'), ("“", "”"), ("'", "'"), ("‘", "’")])
@pytest.mark.parametrize("ellipsis", ["...", "…"])
def test_ellipsis_before_quoted_continuation(opening, closing, ellipsis):
    script = f"She paused{ellipsis} {opening}maybe tomorrow.{closing} Next time."
    a = analyze_script(script)
    assert [s.text for s in a.sentences] == [
        f"She paused{ellipsis} {opening}maybe tomorrow.{closing}", "Next time."
    ]


@pytest.mark.parametrize("following,expected_count", [("We left.", 2), ("we left.", 1)])
@pytest.mark.parametrize("abbreviation", ["p.m.", "a.m.", "etc."])
def test_conditional_abbreviation_before_quote(following, expected_count, abbreviation):
    a = analyze_script(f'We finished at {abbreviation} “{following}”')
    assert len(a.sentences) == expected_count


def test_initial_before_quoted_name():
    a = analyze_script('J. “Jack” Smith arrived. He waved.')
    assert [s.text for s in a.sentences] == ['J. “Jack” Smith arrived.', 'He waved.']


def test_nested_quotes_after_ellipsis():
    a = analyze_script('She paused... “\'maybe tomorrow.\'” Next time.')
    assert [s.text for s in a.sentences] == ['She paused... “\'maybe tomorrow.\'”', 'Next time.']


def test_quoted_ellipsis_before_capital_splits():
    a = analyze_script('She paused… “Tomorrow is better.”')
    assert [s.text for s in a.sentences] == ['She paused…', '“Tomorrow is better.”']


def test_decimals_and_quoted_title_preserve_spans():
    a = analyze_script('“Dr. Smith paid 3.50.” Then he left.')
    assert [s.text for s in a.sentences] == ['“Dr. Smith paid 3.50.”', 'Then he left.']
    for token in a.tokens:
        assert a.text[token.start_char:token.end_char] == token.text
    assert [u.text for u in synthesis_units(a)] == [s.text for s in a.sentences]


def test_short_unpunctuated_fragment_merges():
    a = analyze_script("This is a full sentence.\nYes")
    assert len(a.sentences) == 1


def test_short_punctuated_sentences_stay_separate():
    a = analyze_script("Yes. Wait! Go.")
    assert len(a.sentences) == 3


def test_tokens_map_back_into_text():
    a = analyze_script("Hello, world. It's 2026!")
    for t in a.tokens:
        assert a.text[t.start_char : t.end_char].split()[0] in t.text
    assert [t.norm for t in a.tokens] == ["hello", "world", "its", "2026"]


def test_accents_folded_for_matching():
    a = analyze_script("Café déjà vu.")
    assert [t.norm for t in a.tokens] == ["cafe", "deja", "vu"]


def test_emphasis_markers():
    a = analyze_script("This is *really* big.")
    assert "*" not in a.text
    assert [t.emphasis for t in a.tokens] == [False, False, True, False]


def test_char_count_letters_and_digits_only():
    a = analyze_script("Hi, 42!")
    assert a.char_count == 4


def test_warnings():
    long_sentence = " ".join(["word"] * 40) + "."
    a = analyze_script(f"{long_sentence} Visit www.example.com for $5 deals 🎉 now 2026.")
    codes = {w.code for w in a.warnings}
    assert {"long_sentence", "contains_numbers", "contains_url_or_email",
            "contains_symbols", "contains_emoji"} <= codes


def test_mixed_scripts_warning():
    a = analyze_script("Hello दुनिया.")
    assert "mixed_scripts" in {w.code for w in a.warnings}


def test_very_long_script_warning():
    a = analyze_script("word. " * 3100)
    assert "very_long_script" in {w.code for w in a.warnings}


def test_synthesis_units_split_long_sentences():
    words = ["alpha,"] * 5 + ["beta"] * 70
    a = analyze_script(" ".join(words) + ".")
    assert len(a.sentences) == 1
    units = synthesis_units(a, limit=60)
    assert len(units) >= 2
    assert all(u.token_end - u.token_start <= 60 for u in units)
    assert units[0].token_start == 0 and units[-1].token_end == a.word_count
    assert all(units[i].token_end == units[i + 1].token_start for i in range(len(units) - 1))


def test_synthesis_units_short_sentences_unchanged():
    a = analyze_script("One two. Three four.")
    units = synthesis_units(a)
    assert [u.text for u in units] == ["One two.", "Three four."]


def test_performance_3000_words():
    script = "This is a sentence with several ordinary words in it. " * 300
    t0 = time.perf_counter()
    a = analyze_script(script)
    elapsed = time.perf_counter() - t0
    assert a.word_count == 3000
    assert elapsed < 0.25  # spec says < 50 ms on a dev machine; leave headroom for CI
