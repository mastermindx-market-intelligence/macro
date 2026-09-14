"""Pin packet W9B_REC_RIGHTS: the rights-gate docket excerpt for the F07/F09 BLOCKED_RIGHTS rows
named in the 2026-09-13 16:02Z W9 planner ruling.

The excerpt lives at
`research/market_intelligence_productization/W9_W9B_REC_RIGHTS_2026-09-13.md`.
The suite asserts four pins per ruling R2: the note exists; it carries every row id the W9 planner
named under each heading (035/037 consensus, 020/061 deal-flow, 028 AIS, 030/041 physical-vs-
financial, 068 deal-terms); it never uses a standalone `BUILT` token (the only built-shaped word
the capability_state_c2 vocabulary admits is `BUILT_NOT_PROVEN`); and it carries no Supabase
project reference, no personal access token, and no API key. A 20-letter (or longer) secret-shaped
token is also refused, because the excerpt is plain-language research prose.

This is a research-only pin: the packet that writes the excerpt also writes no row to the F00C CSV,
so this suite reads the excerpt from disk and never touches the ledger. The records lane owns the
ledger; this pin only proves the excerpt is paste-safe.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

NOTE = _ROOT / (
    "research/market_intelligence_productization/"
    "W9_W9B_REC_RIGHTS_2026-09-13.md"
)

# The eight F07/F09 BLOCKED_RIGHTS rows the W9 planner named, in the order the planner gave them.
# Five headings; eight row ids; every row is BLOCKED_RIGHTS / NOT_BUILT on the F00C CSV today.
ROWS = (
    # 035/037 consensus (F07-VALUATION-SCENARIO)
    "MO-PAID-035",
    "MO-PAID-037",
    # 020/061 deal-flow (F09-CAPITAL-MATERIALS)
    "MO-DELTA-020",
    "MO-PAID-061",
    # 028 AIS (F09-CAPITAL-MATERIALS)
    "MO-DELTA-028",
    # 030/041 physical-vs-financial (F09-CAPITAL-MATERIALS)
    "MO-DELTA-030",
    "MO-PAID-041",
    # 068 deal-terms (F09-CAPITAL-MATERIALS)
    "MO-PAID-068",
)

# A standalone-BUILT detector matches the token `BUILT` only when it sits between word boundaries
# AND is not part of `NOT_BUILT` (no `\b` between `_` and `B`) or `BUILT_NOT_PROVEN` (no `\b` between
# `T` and `_`). `\b` in Python `re` matches between `\w` and `\W`; `_` and `B` are both `\w`, so
# neither compound token crosses a boundary and a bare `BUILT` is the only match.
_BUILT_TOKEN = re.compile(r"\bBUILT\b")

# Supabase project references look like `https://<ref>.supabase.co` or `supabase.co/<ref>`.
# Personal Access tokens look like `sbp_` followed by 40 hex-like characters. API keys look like
# `Bearer ` / `sk-` / `eyJ` JWT prefixes. The excerpt is plain-language research prose and carries
# none of these.
_SUPABASE_REF_RE = re.compile(
    r"https?://[A-Za-z0-9_-]+\.supabase\.co|"
    r"supabase\.co/[A-Za-z0-9_-]+"
)
_PAT_RE = re.compile(r"\bsbp_[A-Za-z0-9]{20,}\b")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{16,}\b")
_OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
_ANTHROPIC_KEY_RE = re.compile(r"\bsk-ant-[A-Za-z0-9-]{20,}\b")
# A 20-letter secret-shaped token: 20 contiguous alphanumerics that look like an opaque key, not a
# normal English word. `re` cannot read intent, so the rule is mechanical — a run of 20 letters
# inside an alphanumerics-only block. The excerpt is plain-language prose and so carries none.
_SECRET_RUN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{20,}(?![A-Za-z0-9])")


def _note_text() -> str:
    return NOTE.read_text(encoding="utf-8")


# ------------------------------------------------------------ the note exists


def test_note_exists() -> None:
    assert NOTE.exists(), f"missing W9 rights-gate excerpt: {NOTE}"
    text = _note_text()
    assert text.strip(), f"empty W9 rights-gate excerpt: {NOTE}"


# ------------------------------------------------------------ every row id


@pytest.mark.parametrize("row_id", ROWS)
def test_note_contains_every_row_id(row_id: str) -> None:
    text = _note_text()
    assert row_id in text, (
        f"W9 rights-gate excerpt does not name {row_id!r}; "
        "the excerpt must cover the eight F07/F09 BLOCKED_RIGHTS rows the W9 planner named "
        "under the 035/037, 020/061, 028, 030/041 and 068 headings"
    )


# ------------------------------------------------------------ vocabulary


def test_note_never_uses_built_as_a_standalone_capability_state() -> None:
    """Plain `BUILT` is not in the capability_state_c2 vocabulary.

    The vocabulary is exactly {NOT_BUILT, PARTIAL, BUILT_NOT_PROVEN, SPEC_ONLY, PROVEN_LIVE}.
    `BUILT_NOT_PROVEN` is the only built-shaped token permitted. A standalone `BUILT` would be a
    vocabulary violation and would also be a claim the packet has no build evidence for.
    """
    text = _note_text()
    matches = _BUILT_TOKEN.findall(text)
    assert not matches, (
        f"W9 rights-gate excerpt uses standalone 'BUILT' {len(matches)} time(s); "
        "the vocabulary permits only BUILT_NOT_PROVEN as a built-shaped capability_state_c2 "
        "value, never plain BUILT."
    )


def test_note_never_sets_capability_state_c2_to_proven_live() -> None:
    """`PROVEN_LIVE` is never set by this packet.

    The packet is an EXCERPT; no row moves to `PROVEN_LIVE`. The excerpt must not claim any row
    reaches production live state.
    """
    text = _note_text()
    proven_live_assignments = re.findall(
        r"(?:set|moved to|reached|is now|now reads)\s+PROVEN_LIVE",
        text,
        re.IGNORECASE,
    )
    assert not proven_live_assignments, (
        f"W9 rights-gate excerpt claims a row reached PROVEN_LIVE "
        f"({len(proven_live_assignments)} occurrence(s)); this packet is an excerpt only and "
        "PROVEN_LIVE is never set."
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
        (_SECRET_RUN_RE, "20-letter secret-shaped token"),
    ],
)
def test_note_carries_no_secret_or_supabase_reference(
    pattern: re.Pattern[str], label: str
) -> None:
    text = _note_text()
    matches = pattern.findall(text)
    assert not matches, (
        f"W9 rights-gate excerpt contains a {label}: {matches[0]!r}; "
        "the excerpt is plain-language research prose and must carry no secrets or vendor "
        "project references. A 20-letter run is refused because the excerpt is research prose, "
        "not a credentials document."
    )


# ------------------------------------------------------------ the binding phrase is present


def test_note_quotes_the_binding_rights_gate_phrase() -> None:
    """The excerpt carries the binding phrase the ruling names, verbatim.

    The W9 planner ruling R1 mandates the excerpt quote `no packet may be composed`. The excerpt
    quotes it once as the operative rule and applies it to every row.
    """
    text = _note_text()
    assert "no packet may be composed" in text, (
        "W9 rights-gate excerpt does not quote the binding phrase 'no packet may be composed'; "
        "the W9 planner ruling R1 mandates the excerpt carry that quote and apply it to every "
        "BLOCKED_RIGHTS row the planner named."
    )


# ------------------------------------------------------------ the note names the CSV owner


def test_note_names_the_records_stack_as_csv_owner() -> None:
    text = _note_text()
    assert "PR #7014" in text, (
        "W9 rights-gate excerpt does not name PR #7014 as the CSV owner; the records stack owns "
        "the F00C granular closure ledger and the excerpt must point at it."
    )
    assert "not applied" in text.lower(), (
        "W9 rights-gate excerpt does not state that the moves are not applied; the packet is an "
        "excerpt only and the excerpt must say so."
    )


# ------------------------------------------------------------ the note names every ancestor tip


def test_note_names_the_origin_main_ancestor_tip() -> None:
    text = _note_text()
    assert "321da62b3b01" in text, (
        "W9 rights-gate excerpt does not name the origin/main ancestor tip (321da62b3b01); "
        "the excerpt must cite the ancestor it reads the rows from."
    )


# ------------------------------------------------------------ the note quotes every row id as a marked quote


@pytest.mark.parametrize("row_id", ROWS)
def test_note_quotes_every_row_id_as_a_marked_quote(row_id: str) -> None:
    text = _note_text()
    pattern = re.compile(
        rf"^### {re.escape(row_id)}\s*$", re.MULTILINE
    )
    assert pattern.search(text), (
        f"W9 rights-gate excerpt does not have a `### {row_id}` heading; "
        "every row the W9 planner named must carry its own heading so the records stack can "
        "find the row's quoted block mechanically."
    )


# ------------------------------------------------------------ the note never proposes a CSV edit


def test_note_never_proposes_editing_the_f00c_csv() -> None:
    text = _note_text()
    # The packet is records-only: the CSV is byte-identical to its origin/main form. Any
    # proposal to edit the CSV would be a violation of ruling R0.
    edit_proposals = re.findall(
        r"(?:will|intends to|proposes to|hereby|now)\s+(?:edit|write|apply|mutate|patch)\s+"
        r"(?:the\s+)?(?:F00C|granular closure ledger|csv)",
        text,
        re.IGNORECASE,
    )
    assert not edit_proposals, (
        f"W9 rights-gate excerpt proposes editing the F00C CSV "
        f"({len(edit_proposals)} occurrence(s)); the packet is records-only and the CSV is not "
        "edited here."
    )