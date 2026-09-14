"""Pin packet W9B_REC_F11: the F11 slice of the orchestrator ledger moves.

Drafted 2026-09-13 by the Meta-CEO B seat under the W9 planner ruling. The note
exists at `research/market_intelligence_productization/W9_LEDGER_NOTE_F11_2026-09-13.md`
and proposes — does NOT apply — five ledger moves for the F11 lane. PR #7014
(B-REC-B5-X) owns the F00C CSV; this packet owns the prose and this pin test.

RED before the packet: the note did not exist, no F11 slice was queued behind
#7014, and the five rows had no proposed next state on disk for the records
stack to paste.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
NOTE = _ROOT / (
    "research/market_intelligence_productization/"
    "W9_LEDGER_NOTE_F11_2026-09-13.md"
)

ROWS = (
    "MO-PAID-031",
    "MO-PAID-032",
    "MO-PAID-047",
    "MO-PAID-053",
    "MO-PAID-054",
)

# The five state values the ledger column accepts. The note may move rows inside
# this set; it may never widen the set. PROVEN_LIVE is forbidden in this packet
# (no production readback in hand for any row); a bare BUILT state is also
# forbidden — the only legal BUILT-form is BUILT_NOT_PROVEN.
CAPABILITY_STATES = {"NOT_BUILT", "PARTIAL", "BUILT_NOT_PROVEN", "SPEC_ONLY", "PROVEN_LIVE"}

# Supabase project refs look like `https://<ref>.supabase.co`; service_role/anon
# keys start with `eyJ` (JWT prefix); PATs start with `sbp_` or `pat:`. A bare
# `<ref>.supabase.co` slug with no protocol is also caught.
_SUPABASE_PATTERNS = (
    re.compile(r"https?://[A-Za-z0-9-]+\.supabase\.co", re.IGNORECASE),
    re.compile(r"\bsbp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?<![\w.-])[A-Za-z0-9]{20,}\.supabase\.co\b", re.IGNORECASE),
    re.compile(r"\bpat[A-Za-z0-9]{20,}\b", re.IGNORECASE),
)


def _note_text() -> str:
    return NOTE.read_text(encoding="utf-8")


# ------------------------------------------------------------ the note exists and names its rows


def test_note_exists() -> None:
    assert NOTE.exists(), f"missing F11 ledger note: {NOTE}"


@pytest.mark.parametrize("row_id", ROWS)
def test_note_names_every_row(row_id: str) -> None:
    text = _note_text()
    assert row_id in text, f"note must name row {row_id}"


def test_note_names_every_row_at_least_twice() -> None:
    """Each row should appear in its own section header AND in the summary
    table; this test catches a header-without-table regression."""
    text = _note_text()
    for row_id in ROWS:
        assert text.count(row_id) >= 2, f"row {row_id} should appear in header and table"


# ------------------------------------------------------------ the vocabulary


@pytest.mark.parametrize("state", CAPABILITY_STATES)
def test_note_references_every_allowed_state_at_least_once(state: str) -> None:
    """The summary table must cite each allowed state at least once so a
    records reader can see the full vocabulary in one place."""
    text = _note_text()
    assert state in text, f"note should reference state {state} at least once"


def test_note_does_not_set_proven_live() -> None:
    """PROVEN_LIVE is forbidden in this packet — no row carries a production
    readback. The note may name the state in the vocabulary list and in rule
    statements; it must not bind it to any row.

    The row-binding shapes this test catches:
      - "Proposed `capability_state_c2`: `PROVEN_LIVE`"
      - a summary-table row whose `Proposed state` cell reads `PROVEN_LIVE`.
    """
    text = _note_text()
    proposed_binding = re.findall(
        r"Proposed\s+`capability_state_c2`:\s*`PROVEN_LIVE`", text
    )
    assert not proposed_binding, (
        f"note must not bind PROVEN_LIVE to any row's capability_state_c2: "
        f"{proposed_binding}"
    )
    table_cell = re.findall(r"\|\s*PROVEN_LIVE\s*\|", text)
    assert not table_cell, (
        f"note must not list PROVEN_LIVE as a row value in any table cell: "
        f"{table_cell}"
    )


def test_note_does_not_use_bare_built_as_a_state() -> None:
    """A bare `BUILT` (without the `_NOT_PROVEN` suffix) is a forbidden
    standalone state in this packet. The only legal BUILT-form is
    `BUILT_NOT_PROVEN`. Detect the standalone token in state-attribute
    positions (after `|`, `:`, or `to`)."""
    text = _note_text()
    bad = re.findall(r"(?:\||:|->|to\s)\s*BUILT\b(?!\s*_NOT_PROVEN)", text)
    assert not bad, f"note must not use bare BUILT as a state value: {bad}"


# ------------------------------------------------------------ no Supabase project reference, PAT, or key


def test_note_has_no_supabase_project_url() -> None:
    text = _note_text()
    for pattern in _SUPABASE_PATTERNS:
        match = pattern.search(text)
        assert match is None, (
            f"note must not carry a Supabase project reference / PAT / key: "
            f"matched {match.group(0)!r}"
        )


def test_note_does_not_inline_an_anon_or_service_role_key() -> None:
    """A JWT prefix `eyJ` followed by three base64 segments is the canonical
    shape of a Supabase anon/service_role key; flag any inline literal."""
    text = _note_text()
    jwt_literal = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
    assert not jwt_literal.search(text), "note must not inline a Supabase key"


# ------------------------------------------------------------ the packet shape


def test_note_records_only_no_code_intent() -> None:
    """This packet is a note + a pin test. It must not propose a code edit to
    the F00C CSV or to the Terminal master."""
    text = _note_text()
    assert "records only" in text.lower()
    assert "#7014" in text, "note must name PR #7014 as the CSV owner"


def test_note_cites_ancestors_for_every_row() -> None:
    """Each row's merge citation OR ancestor contract must be named; this is
    the binding evidence the records stack reads."""
    text = _note_text()
    assert "MARKET_ONTOLOGY_F11_POST_VERTICAL_CONTRACT_2026-09-06.md" in text
    assert "terminal#520" in text or "8255f482" in text, (
        "MO-PAID-053's merge citation must be named (terminal#520 / 8255f482)"
    )
    assert "falsifier_tripwires" in text, (
        "MO-PAID-047's ancestor (engine/falsifier_tripwires.py) must be named"
    )
    assert "brain_gateway" in text or "api/brain" in text.lower(), (
        "MO-PAID-054's ancestor (brain_gateway /api/brain) must be named"
    )
