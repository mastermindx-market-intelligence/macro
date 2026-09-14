"""Pin packet W9B_REC_F07: the F07 slice of orch/w8/LEDGER_MOVES.md.

The note lives at
`research/market_intelligence_productization/W9_LEDGER_NOTE_F07_2026-09-13.md`.
The suite asserts four pins: the note exists, it lists every F07 row id, it never
sets capability_state_c2 to plain `BUILT` (the only built-shaped token the
vocabulary admits is `BUILT_NOT_PROVEN`), and it carries no Supabase project
reference, no PAT, and no API key.

This is a research-only pin: the packet that writes the note also writes no row to
the F00C CSV, so this suite reads the note from disk and never touches the
ledger. The records lane owns the ledger; this pin only proves the note is paste-safe.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

NOTE = _ROOT / (
    "research/market_intelligence_productization/"
    "W9_LEDGER_NOTE_F07_2026-09-13.md"
)

# The four F07 rows the F07 slice covers, in CSV order.
ROWS = (
    "MO-PAID-022",
    "MO-PAID-026",
    "MO-DELTA-017",
    "MO-PAID-035",
)

# A standalone-BUILT detector matches the token `BUILT` only when it sits
# between word boundaries AND is not part of `NOT_BUILT` (no `\b` between `_`
# and `B`) or `BUILT_NOT_PROVEN` (no `\b` between `T` and `_`). `\b` in Python
# `re` matches between `\w` and `\W`; `_` and `B` are both `\w`, so neither
# compound token crosses a boundary and a bare `BUILT` is the only match.
_BUILT_TOKEN = re.compile(r"\bBUILT\b")

# Supabase project references look like `https://<ref>.supabase.co` or
# `supabase.co/<ref>`. Personal Access Tokens look like `sbp_` followed by
# 40 hex-like characters. API keys look like `Bearer ` / `sk-` / `eyJ` JWT
# prefixes. The note is plain-language research prose and carries none of these.
_SUPABASE_REF_RE = re.compile(
    r"https?://[A-Za-z0-9_-]+\.supabase\.co|"
    r"supabase\.co/[A-Za-z0-9_-]+"
)
_PAT_RE = re.compile(r"\bsbp_[A-Za-z0-9]{20,}\b")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{16,}\b")
_OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
_ANTHROPIC_KEY_RE = re.compile(r"\bsk-ant-[A-Za-z0-9-]{20,}\b")


def _note_text() -> str:
    return NOTE.read_text(encoding="utf-8")


# ------------------------------------------------------------ the note exists


def test_note_exists() -> None:
    assert NOTE.exists(), f"missing W9 F07 ledger note: {NOTE}"
    text = _note_text()
    assert text.strip(), f"empty W9 F07 ledger note: {NOTE}"


# ------------------------------------------------------------ every row id


@pytest.mark.parametrize("row_id", ROWS)
def test_note_contains_every_row_id(row_id: str) -> None:
    text = _note_text()
    assert row_id in text, (
        f"W9 F07 ledger note does not name {row_id!r}; "
        "the note must cover MO-PAID-022, MO-PAID-026, MO-DELTA-017 and MO-PAID-035"
    )


# ------------------------------------------------------------ vocabulary


def test_note_never_uses_built_as_a_standalone_capability_state() -> None:
    """Plain `BUILT` is not in the capability_state_c2 vocabulary.

    The vocabulary is exactly {NOT_BUILT, PARTIAL, BUILT_NOT_PROVEN, SPEC_ONLY,
    PROVEN_LIVE}. `BUILT_NOT_PROVEN` is the only built-shaped token permitted.
    A standalone `BUILT` would be a vocabulary violation and would also be a
    claim the packet has no build evidence for.
    """
    text = _note_text()
    matches = _BUILT_TOKEN.findall(text)
    assert not matches, (
        f"W9 F07 ledger note uses standalone 'BUILT' {len(matches)} time(s); "
        "the vocabulary permits only BUILT_NOT_PROVEN as a built-shaped "
        "capability_state_c2 value, never plain BUILT."
    )


def test_note_never_sets_capability_state_c2_to_proven_live() -> None:
    """`PROVEN_LIVE` is never set by this packet.

    The packet is a NOTE; no row moves to `PROVEN_LIVE`. The note must not
    claim any row reaches production live state.
    """
    text = _note_text()
    # Search for `PROVEN_LIVE` not preceded by `_` (to avoid e.g. a hypothetical
    # `_PROVEN_LIVE` token that would itself be a vocabulary violation). A line
    # that says e.g. "PROVEN_LIVE never set" is allowed; we only forbid rows
    # being moved there. The packet's stated rule is checked below.
    proven_live_assignments = re.findall(
        r"(?:set|moved to|reached|is now|now reads)\s+PROVEN_LIVE",
        text,
        re.IGNORECASE,
    )
    assert not proven_live_assignments, (
        f"W9 F07 ledger note claims a row reached PROVEN_LIVE "
        f"({len(proven_live_assignments)} occurrence(s)); "
        "this packet is a note only and PROVEN_LIVE is never set."
    )


# ------------------------------------------------------------ secrets scan


@pytest.mark.parametrize(
    "pattern,label",
    [
        (_SUPABASE_REF_RE, "Supabase project reference"),
        (_PAT_RE, "Supabase Personal Access Token"),
        (_JWT_RE, "JWT bearer token"),
        (_BEARER_RE, "Bearer authorization header"),
        (_OPENAI_KEY_RE, "OpenAI-style API key"),
        (_ANTHROPIC_KEY_RE, "Anthropic-style API key"),
    ],
)
def test_note_carries_no_secret_or_supabase_reference(
    pattern: re.Pattern[str], label: str
) -> None:
    text = _note_text()
    matches = pattern.findall(text)
    assert not matches, (
        f"W9 F07 ledger note contains a {label}: {matches[0]!r}; "
        "the note is plain-language research prose and must carry no secrets "
        "or vendor project references."
    )


# ------------------------------------------------------------ the four rows all appear


def test_note_lists_every_f07_row_at_least_once() -> None:
    text = _note_text()
    for row in ROWS:
        # Each row id must appear at least twice: once as the named row it
        # owns, and once inside the summary table that re-lists the moves.
        # A single occurrence would mean the row escaped the summary index.
        assert text.count(row) >= 2, (
            f"row {row} appears {text.count(row)} time(s) in the W9 F07 "
            "ledger note; the note must name each row in its own move block "
            "AND in the summary index, never only in one."
        )


# ------------------------------------------------------------ the note names the CSV owner


def test_note_names_the_records_stack_as_csv_owner() -> None:
    text = _note_text()
    assert "PR #7014" in text, (
        "W9 F07 ledger note does not name PR #7014 as the CSV owner; "
        "the records stack owns the F00C granular closure ledger and the note "
        "must point at it."
    )
    assert "not applied" in text.lower(), (
        "W9 F07 ledger note does not state that the moves are not applied; "
        "the packet is a note only and the note must say so."
    )


# ------------------------------------------------------------ the note names every ancestor tip


def test_note_names_the_origin_main_ancestor_tip() -> None:
    text = _note_text()
    assert "321da62b3b01" in text, (
        "W9 F07 ledger note does not name the origin/main ancestor tip "
        "(321da62b3b01); the note must cite the ancestor it reads the rows "
        "from."
    )


# ------------------------------------------------------------ the note quotes every row verbatim


@pytest.mark.parametrize("row_id", ROWS)
def test_note_quotes_every_row_id_as_a_marked_quote(row_id: str) -> None:
    """Every row id appears at least once as a Markdown heading or bold token.

    The note must mark every row id as a heading (`## ...`) or as a bold lead
    (`**Row id:** ...`) so the records stack can paste the move verbatim.
    A bare inline mention is not enough.
    """
    text = _note_text()
    heading = re.search(rf"^#{1,6}\s+.*{re.escape(row_id)}", text, re.MULTILINE)
    bold = re.search(rf"\*\*[^*]*{re.escape(row_id)}[^*]*\*\*", text)
    assert heading is not None or bold is not None, (
        f"W9 F07 ledger note does not mark {row_id!r} as a heading or bold "
        "lead; the records stack pastes moves from marked blocks."
    )