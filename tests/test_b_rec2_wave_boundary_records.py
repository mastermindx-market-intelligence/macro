"""Pin B-REC-2 review-r2 organizational-memory facts.

RED on previous head 153f02f2: the DEC bound comment 5563321750 to
terminal#514 as the 0013 receipt; the handoff named neither #6958 nor
#6961/#6963 as owed; receipt 0012 committed a live project_ref.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEC = REPO / (
    "agentos/decisions/"
    "DEC-SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06.md"
)
HANDOFF = REPO / "agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-07.md"
RECEIPT_0012 = REPO / (
    "research/market_intelligence_productization/receipts/"
    "supabase_receipt_0012_thesis_objects_2026-09-06.json"
)


def test_0013_receipt_comment_is_on_terminal_513_not_514() -> None:
    text = DEC.read_text(encoding="utf-8")
    assert "5563321750" in text
    assert "terminal#513" in text
    assert "terminal#514 comment id 5563321750" not in text
    assert "Not on #514" in text


def test_handoff_lists_unmerged_6958_6961_6963_as_owed() -> None:
    text = HANDOFF.read_text(encoding="utf-8")
    assert "Owed spec items 4-6" in text
    for pr in ("#6958", "#6961", "#6963"):
        assert pr in text, f"handoff must name owed {pr}"
    assert "e0d39027" in text
    assert "96a0056c" in text
    assert "75a47061" in text


def test_receipt_0012_project_ref_is_placeholder() -> None:
    data = json.loads(RECEIPT_0012.read_text(encoding="utf-8"))
    assert data.get("project_ref") == "{ref}"


def test_dec_and_handoff_agree_0015_carrier_is_514() -> None:
    dec = DEC.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    assert "applies 0014 then 0015 after #514 merges" in dec
    assert "Do not wait on #526 to apply 0015" in dec
    assert "apply 0014 then 0015 after Terminal #514 merges" in handoff
    assert "not the 0015 SQL carrier" in handoff
