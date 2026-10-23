"""View-model unit contract for lib.glossary."""
from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest

from lib import config
from lib.glossary import (
    BANNED_GLANCE_PATTERNS,
    BANNED_GLANCE_TOKENS,
    GLOSSARY_DOMAINS,
    GLOSSARY_MIN_TERMS,
    GLOSSARY_TERMS,
    glossary_view_model,
    validate_glossary,
)

ROOT = config.ROOT

_CONTENT_STOPWORDS = frozenset(
    """
    the a an and or but if when than then that this these those is are be been
    being not never no nor of to in on for with without from by as at it its
    their there here you your we our they them he she his her will would can
    could may might must shall should do does done have has had
    """.split()
)

# Internal state enums that the dashboards render in plain words. They are not
# in lib.glossary.BANNED_GLANCE_TOKENS (which is frozen by the ruling) but they
# are machine text on a public page all the same — review round 2, MAJOR 3 /
# MINOR 1: `SPLIT`, `FLOW` and `SELECTION` reached user copy from the payload.
_INTERNAL_ENUM_TOKENS = frozenset(
    """
    SPLIT FLOW SELECTION ACCUMULATING TRIMMING CONTESTED ENTRY RAN_LATE
    STALE CURRENT UNKNOWN
    """.split()
)


_HEADING_RE = re.compile(r"^#{2,4}\s")


def _source_sections(path: Path) -> list[dict]:
    """Split a ``docs/site_semantics`` file into its heading sections.

    ``validate_glossary`` binds a term to a ``##``/``###``/``####`` heading, so
    the splitter accepts the same three levels.
    """
    sections: list[dict] = []
    current: dict | None = None
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if _HEADING_RE.match(line):
            current = {"line": lineno, "body": []}
            sections.append(current)
        elif current is not None:
            current["body"].append(line)
    return sections


def _so_what(section: dict) -> str:
    for line in section["body"]:
        if line.strip().startswith("- **So what:**"):
            return line.split("- **So what:**", 1)[1]
    return ""


_CJK_RE = re.compile(r"[一-鿿]")


def _content_words(text: str) -> set[str]:
    """EN: 4+ alphanumeric tokens after stopword removal.
    CJK: overlapping character bigrams (each pair of adjacent CJK codepoints).
    """
    if _CJK_RE.search(text):
        # Overlapping CJK bigrams over runs of CJK characters.
        chars: list[str] = []
        for ch in text:
            if "一" <= ch <= "鿿":
                chars.append(ch)
        return {"".join(chars[i : i + 2]) for i in range(len(chars) - 1)}
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) >= 4 and word not in _CONTENT_STOPWORDS
    }


def _fidelity(claim: str, source: str) -> float:
    """Share of ``claim``'s content words that the ``source`` sentence carries."""
    words = _content_words(claim)
    if not words:
        return 0.0
    return len(words & _content_words(source)) / len(words)


def test_glossary_defines_at_least_fifty_terms():
    assert len(GLOSSARY_TERMS) >= GLOSSARY_MIN_TERMS


def test_every_term_binds_to_an_existing_source_heading_line():
    for term in GLOSSARY_TERMS:
        path = ROOT / term.source_file
        lines = path.read_text(encoding="utf-8").splitlines()
        actual = lines[term.source_line - 1].strip()
        assert actual in (
            f"### {term.source_heading}",
            f"#### {term.source_heading}",
            f"## {term.source_heading}",
        ), f"{term.id}: {actual!r} does not match {term.source_heading!r}"


def test_term_ids_are_unique_kebab_case():
    ids = [t.id for t in GLOSSARY_TERMS]
    assert len(ids) == len(set(ids))
    for i in ids:
        assert re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", i)


def test_every_term_carries_english_and_chinese_name_and_answer():
    for term in GLOSSARY_TERMS:
        assert term.name_en.strip()
        assert term.name_zh.strip()
        assert term.answer_en.strip()
        assert term.answer_zh.strip()


def test_glance_answers_respect_the_word_and_character_budgets():
    for term in GLOSSARY_TERMS:
        assert len(term.answer_en.split()) <= 30, term.id
        assert len(term.answer_zh) <= 60, term.id
        assert (term.why_en is None) == (term.why_zh is None), term.id
        if term.why_en is not None:
            assert len(term.why_en.split()) <= 20, term.id
            assert len(term.why_zh) <= 40, term.id


def test_every_term_carries_a_why_pair():
    """B-F13-1 audit heal (m#6909): every glossary term must carry a non-empty
    ``why_en`` and ``why_zh`` pair so the page's "what you do about it"
    promise is honoured on every row, not just 15 of 54. The both-or-neither
    invariant at lib/glossary.py:401 is the schema half; this is the count
    half — any term without a pair must fail here so the build is closed."""
    for term in GLOSSARY_TERMS:
        assert term.why_en is not None and term.why_en.strip(), term.id
        assert term.why_zh is not None and term.why_zh.strip(), term.id


def test_sue_row_carries_the_demotion_with_no_digit_in_either_why_field():
    """B-F13-1 audit heal (m#6909) H2: the SUE row's own bound source records
    the cross-sectional IC collapsing to near zero, so the why pair must
    restate the measured position without inventing a number, weight, or
    IC value in user copy."""
    sue = next(t for t in GLOSSARY_TERMS if t.id == "sue-earnings-chip")
    assert sue.why_en and sue.why_en.strip()
    assert sue.why_zh and sue.why_zh.strip()
    assert not any(c.isdigit() for c in sue.why_en), sue.why_en
    assert not any(c.isdigit() for c in sue.why_zh), sue.why_zh


def test_every_why_line_is_transcribed_from_its_own_bound_so_what():
    """B-F13-1 review round 2, BLOCKERS 2-3 and MAJORS 1-2: three ETF rows had
    a ``why`` transcribed from the PRECEDING section's ``**So what:**`` — an
    off-by-one-heading error that published one panel's advice on another
    panel's row (`forward-windows-etfs` claimed the counts "tell non-members
    how much evidence backs the board" while its own source says the record
    backs nothing; `fund-coverage-table` and `rotation-backdrop` were a swap
    pair). A row whose ``why`` is closer to some OTHER section's So-what than
    to its own is that defect, so the binding is measured, not assumed."""
    cache: dict[Path, list[dict]] = {}
    for term in GLOSSARY_TERMS:
        path = ROOT / term.source_file
        if path not in cache:
            cache[path] = _source_sections(path)
        sections = cache[path]
        own = next((s for s in sections if s["line"] == term.source_line), None)
        assert own is not None, f"{term.id}: bound section not found at line {term.source_line}"
        own_so_what = _so_what(own)
        if not own_so_what.strip():
            continue  # bound section carries no So-what bullet to transcribe
        own_score = _fidelity(term.why_en or "", own_so_what)
        for other in sections:
            if other is own:
                continue
            other_so_what = _so_what(other)
            if not other_so_what.strip():
                continue
            other_score = _fidelity(term.why_en or "", other_so_what)
            assert own_score >= other_score, (
                f"{term.id}: why_en matches {term.source_file}:{other['line']} "
                f"({other_score:.2f}) better than its own bound So-what at "
                f"{term.source_file}:{own['line']} ({own_score:.2f}) — the row is "
                f"transcribed from the wrong heading: {term.why_en!r}"
            )


# why_zh vs answer_zh CJK-bigram overlap. Bound So-whats are English-only
# (measured at bcba723c: 53 rows, source_has_cjk=0, histogram {0.0: 53}), so
# scoring why_zh against the So-what was vacuous. The two ZH strings of one
# row must share vocabulary; a swapped why_zh from the next row must not.
_ZH_VOCAB_THRESHOLD = 0.05


def test_content_words_takes_cjk_bigrams_from_mixed_script():
    assert _content_words("RAN / LATE 信号已过") == {"信号", "号已", "已过"}


def test_why_zh_shares_vocabulary_with_its_own_answer_zh():
    """h_7125 r3 MAJOR-1: score why_zh against the same row's answer_zh.

    The previous check compared why_zh to the bound English So-what, so every
    score was 0.0 and swapping why_zh across rows never failed. The two ZH
    strings of one glossary row must share CJK character-bigram vocabulary;
    replacing why_zh with the next row's why_zh must fall to or below the
    threshold. At this head, real_min is 0.0556 and swap_max is 0.0476;
    consensus-board, persistence-streak, and pullback-risk-radar stay inside
    0.05 of the 0.05 floor because a faithful why_zh cannot borrow more of
    those rows' answer_zh.
    """
    n = len(GLOSSARY_TERMS)
    for i, term in enumerate(GLOSSARY_TERMS):
        own = _fidelity(term.why_zh or "", term.answer_zh or "")
        assert own > _ZH_VOCAB_THRESHOLD, (
            f"{term.id}: why_zh shares no vocabulary with its own answer_zh "
            f"({own:.3f} <= {_ZH_VOCAB_THRESHOLD}): why={term.why_zh!r} "
            f"answer={term.answer_zh!r}"
        )
        nxt = GLOSSARY_TERMS[(i + 1) % n]
        swapped = _fidelity(nxt.why_zh or "", term.answer_zh or "")
        assert swapped <= _ZH_VOCAB_THRESHOLD, (
            f"{term.id}: swapped why_zh from {nxt.id} still matches answer_zh "
            f"({swapped:.3f} > {_ZH_VOCAB_THRESHOLD})"
        )


def test_no_why_line_repeats_its_own_answer():
    """B-F13-1 review round 2, MAJOR 2 / MINOR 4: `measurement-windows` and
    `market-tiles-china` printed their own ``answer`` a second time in the
    ``why`` slot, so the row showed one sentence twice and delivered no read —
    the exact defect H1 exists to heal. The ``why`` must come from the bound
    ``**So what:**``, which is a different sentence from the ``**Means:**``
    the answer restates."""
    for term in GLOSSARY_TERMS:
        overlap = _fidelity(term.why_en or "", term.answer_en)
        assert overlap <= 0.6, (
            f"{term.id}: why_en repeats {overlap:.0%} of answer_en's content "
            f"words — the row says the same thing twice: {term.why_en!r}"
        )


def test_public_copy_never_names_an_internal_enum_state():
    """B-F13-1 review round 2, MAJOR 3 / MINOR 1: `consensus-board` put the raw
    payload enum `SPLIT` into public copy (the board itself renders that state
    as "they disagree" / 「存在分歧」) and `flow-vs-selection` did the same with
    `FLOW` / `SELECTION` (rendered as "Investor money" / "Manager picks"). The
    ZH side already translated them, so EN and ZH disagreed. Plain-language law:
    the user sees the sentence the page renders, never the enum behind it."""
    for term in GLOSSARY_TERMS:
        for field in ("name_en", "name_zh", "answer_en", "answer_zh", "why_en", "why_zh"):
            text = getattr(term, field) or ""
            for token in re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", text):
                assert token not in _INTERNAL_ENUM_TOKENS, f"{term.id}.{field}: {token} in {text!r}"


@pytest.mark.parametrize(
    "term_id, en_hedge, zh_hedge",
    [
        ("sector-heat-strip", "may", "可能"),
        ("persistence-streak", "may", "可能"),
        ("washout-chip", "typically", "通常"),
        # MAJOR-1 h_7125: "Net near zero with a high gross figure means the funds
        # are trading against each other" — the gross qualifier is the load-bearing
        # part; drop it and the row implies near-zero net IS the signal rather
        # than the absence of one.
        ("net-conviction", "gross", "总额"),
    ],
)
def test_a_hedge_the_source_carries_survives_into_the_why_line(term_id, en_hedge, zh_hedge):
    """B-F13-1 review round 2, MAJOR 5: H1 forbids weakening a qualifier the
    source carries, and three rows turned a hedge into a frequency claim —
    "the move **may** be narrow" became "usually means a narrow move", "a
    position that **may** be finished" became "Flat means done.", and
    "**typically** a higher-quality entry" became an unqualified "beat". The
    hedge is the claim, so it is pinned in both languages.

    h_7125 MAJOR-1: the gross-qualifier on net-conviction is not a hedge but
    the load-bearing condition — without it the row says near-zero net IS the
    signal, when the source says the opposite. Pinned identically in both
    languages."""
    term = next(t for t in GLOSSARY_TERMS if t.id == term_id)
    assert en_hedge in (term.why_en or "").lower(), term.why_en
    assert zh_hedge in (term.why_zh or ""), term.why_zh


def test_stage_labels_en_uses_the_chip_text_the_page_renders():
    """h_7125 MAJOR-2 MINOR-3: the EN answer for stage-labels-cn says "Ran Late"
    but the page renders ``bi('RAN / LATE', '信号已过')`` — the slash form is
    what a reader sees, so the answer must use it."""
    term = next(t for t in GLOSSARY_TERMS if t.id == "stage-labels-cn")
    assert "RAN / LATE" in (term.answer_en or ""), term.answer_en
    # The slash form must appear, not the bare "Ran Late" that round 1 used.
    assert "Ran Late" not in (term.answer_en or "").replace("RAN / LATE", ""), term.answer_en


def test_stage_labels_zh_uses_the_chip_text_the_page_renders():
    """h_7125 MAJOR-2: the ZH answer for stage-labels-cn carries 「已迟」 which
    the page never renders — templates/stocktable.js line ~1173 renders
    ``bi('RAN / LATE', '信号已过')``. Both the answer_zh and why_zh must use
    the rendered chip text. (answer_zh 「已迟」 is m#6909 copy; the heal scope
    covers the why_zh already, and answer_zh is repaired here as part of the
    same defect class.)"""
    term = next(t for t in GLOSSARY_TERMS if t.id == "stage-labels-cn")
    assert "信号已过" in (term.answer_zh or ""), term.answer_zh
    assert "信号已过" in (term.why_zh or ""), term.why_zh
    # MINOR-2c: the dead chip text must not appear in any glossary field.
    for entry in GLOSSARY_TERMS:
        for field in ("answer_zh", "why_zh", "answer_en", "why_en"):
            assert "已迟" not in (getattr(entry, field) or ""), f"{entry.id}.{field}"


def test_stage_labels_coupling_test():
    """h_7125 MAJOR-2: templates/stocktable.js:~1173 renders
    ``bi('RAN / LATE', '信号已过')`` for the RAN/LATE stage chip.
    The glossary stage-labels-cn entry must use exactly those strings
    (EN answer, ZH answer, ZH why) so the row matches what the page shows.

    RED on 89ec6f2c: the row carried 'Ran Late' / '已迟' — neither matches
    the JS. GREEN at HEAD: all three fields carry the exact bi() strings."""
    import subprocess

    js_text = subprocess.check_output(
        ["git", "show", f"HEAD:templates/stocktable.js"], text=True, encoding="utf-8"
    )
    m = re.search(
        r"bi\s*\(\s*['\"]\s*(RAN\s*/\s*LATE)\s*['\"]\s*,\s*['\"]\s*(信号已过)\s*['\"]\s*\)",
        js_text,
    )
    assert m, "bi('RAN / LATE', '信号已过') pattern not found in stocktable.js"
    chip_en = m.group(1)
    chip_zh = m.group(2)

    term = next(t for t in GLOSSARY_TERMS if t.id == "stage-labels-cn")
    assert chip_en in (term.answer_en or ""), (
        f"RAN/LATE chip EN {chip_en!r} not in stage-labels-cn answer_en: {term.answer_en!r}"
    )
    assert chip_zh in (term.answer_zh or ""), (
        f"RAN/LATE chip ZH {chip_zh!r} not in stage-labels-cn answer_zh: {term.answer_zh!r}"
    )
    assert chip_zh in (term.why_zh or ""), (
        f"RAN/LATE chip ZH {chip_zh!r} not in stage-labels-cn why_zh: {term.why_zh!r}"
    )


def test_consensus_board_why_uses_the_boards_own_words():
    """h_7125 MINOR-1: the row must name the board's own words so a reader
    can match the row to the board indicator they see. templates/_etf_board_rows.html.j2
    line ~44 renders ``bi('they disagree', '存在分歧')`` for the contested state."""
    term = next(t for t in GLOSSARY_TERMS if t.id == "consensus-board")
    # EN: the board renders "they disagree".
    assert "they disagree" in (term.why_en or "").lower(), term.why_en
    # ZH: the board renders 「存在分歧」.
    assert "存在分歧" in (term.why_zh or ""), term.why_zh


def test_glance_text_carries_no_banned_vocabulary():
    for term in GLOSSARY_TERMS:
        for text in (
            term.name_en, term.name_zh,
            term.answer_en, term.answer_zh, term.why_en or "", term.why_zh or "",
        ):
            for pattern in BANNED_GLANCE_PATTERNS:
                assert not pattern.search(text), f"{term.id}: banned pattern in {text!r}"
            for token in re.findall(r"[A-Za-z0-9_]+", text):
                assert token not in BANNED_GLANCE_TOKENS, f"{term.id}: banned token {token!r}"


def test_validate_glossary_rejects_a_banned_token_in_the_visible_term_name():
    """review round 2, MINOR 1: validate_glossary only ran the banned-vocab
    gate over answer_en/zh/why_en/zh — name_en/name_zh are rendered visible
    text too (templates/glossary.html.j2) and were never checked."""
    bad = replace(GLOSSARY_TERMS[0], name_en="RISK_OFF Signal")
    terms = (bad,) + GLOSSARY_TERMS[1:]
    with pytest.raises(ValueError):
        validate_glossary(ROOT, terms)


def test_validate_glossary_rejects_a_term_whose_source_line_does_not_match():
    bad = replace(GLOSSARY_TERMS[0], source_line=GLOSSARY_TERMS[0].source_line + 1)
    terms = (bad,) + GLOSSARY_TERMS[1:]
    with pytest.raises(ValueError):
        validate_glossary(ROOT, terms)


def test_validate_glossary_rejects_an_over_budget_answer():
    bad = replace(GLOSSARY_TERMS[0], answer_en=" ".join(["word"] * 31))
    terms = (bad,) + GLOSSARY_TERMS[1:]
    with pytest.raises(ValueError):
        validate_glossary(ROOT, terms)


def test_every_frozen_domain_carries_terms_and_no_unknown_domain_appears():
    domain_ids = {d.id for d in GLOSSARY_DOMAINS}
    seen = {t.domain for t in GLOSSARY_TERMS}
    assert seen <= domain_ids
    for domain in GLOSSARY_DOMAINS:
        assert any(t.domain == domain.id for t in GLOSSARY_TERMS), domain.id


def test_view_model_prints_all_twenty_six_letters_including_empty_ones():
    vm = glossary_view_model(ROOT)
    assert len(vm["letters"]) == 26
    assert [l["id"] for l in vm["letters"]] == [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    assert any(l["count"] == 0 for l in vm["letters"])


def test_letter_anchor_is_set_exactly_once_per_occupied_letter():
    vm = glossary_view_model(ROOT)
    for domain in vm["domains"]:
        seen = set()
        for term in domain["terms"]:
            if term["letter_anchor"]:
                assert term["letter"] not in seen
                seen.add(term["letter"])


def test_search_index_gives_zh_readers_the_same_definition_reach_as_en_readers():
    """review round 2, MINOR 2: `search` indexed name_en/name_zh/answer_en but
    not answer_zh, so an EN reader could find a term by words in its
    definition and a ZH reader could only find it by the headword itself."""
    vm = glossary_view_model(ROOT)
    for domain in vm["domains"]:
        for term in domain["terms"]:
            assert term["answer_zh"] in term["search"], term["id"]
