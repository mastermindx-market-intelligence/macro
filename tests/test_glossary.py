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


def _content_words(text: str) -> set[str]:
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
    ],
)
def test_a_hedge_the_source_carries_survives_into_the_why_line(term_id, en_hedge, zh_hedge):
    """B-F13-1 review round 2, MAJOR 5: H1 forbids weakening a qualifier the
    source carries, and three rows turned a hedge into a frequency claim —
    "the move **may** be narrow" became "usually means a narrow move", "a
    position that **may** be finished" became "Flat means done.", and
    "**typically** a higher-quality entry" became an unqualified "beat". The
    hedge is the claim, so it is pinned in both languages."""
    term = next(t for t in GLOSSARY_TERMS if t.id == term_id)
    assert en_hedge in (term.why_en or "").lower(), term.why_en
    assert zh_hedge in (term.why_zh or ""), term.why_zh


def test_zh_stage_label_copy_uses_the_label_the_page_actually_renders():
    """B-F13-1 review round 2, MINOR 3: the ZH label 「已迟」 appears nowhere on
    the rendered page — templates/stocktable.js renders
    ``bi('RAN / LATE', '信号已过')`` — so the new why pair must name the label a
    reader can actually find. (The pre-existing ``answer_zh`` that first carried
    「已迟」 is m#6909 copy and out of this heal's scope; this pins the field the
    heal added.)"""
    term = next(t for t in GLOSSARY_TERMS if t.id == "stage-labels-cn")
    assert "信号已过" in (term.why_zh or ""), term.why_zh
    for entry in GLOSSARY_TERMS:
        assert "已迟" not in (entry.why_zh or ""), entry.id


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
