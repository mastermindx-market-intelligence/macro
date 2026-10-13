"""R10 fixture ids and first-vertical witness resolution.

Runs on the existing public-render-fastlane job (gate: code, pytest only).
The reads are JSON and markdown path literals under research/finance, so the
suite does not import engine code.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIXTURE = "research/finance/FINANCE_R10_GLOBAL_REGIONAL_CASEBOOK_FIXTURE_V0_1_2026-09-23.json"
SYNTHESIS = "research/finance/FINANCE_R10_CASE_SYNTHESIS_MATRIX_V0_1_2026-09-23.json"
R10D_JSON = "research/finance/FINANCE_R10D_CREDIT_UNDERWRITING_MEASUREMENTS_V0_1_2026-09-23.json"
R10D_MD = "research/finance/FINANCE_R10D_CREDIT_UNDERWRITING_RERATING_2026-09-23.md"
PACKET = "research/finance/FINANCE_FIRST_VERTICAL_ASSERTION_PACKET_V0_1_2026-09-23.json"
R12 = "research/finance/FINANCE_R12_INTEGRATION_PREFLIGHT_V0_1_2026-09-24.json"
HANDOFF = (
    ROOT
    / "agentos"
    / "handoffs"
    / "GMI-FINANCE-MASTER-FABLE-CEO-HANDOFF-2026-09-24.md"
)


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_r10_synthesis_rows_use_fixture_ids() -> None:
    fixture = _load(FIXTURE)
    synthesis = _load(SYNTHESIS)
    cases = fixture["cases"]
    rows = synthesis["cases"]
    assert len(cases) == 12
    assert len(rows) == 12
    by_canonical = {row["canonical_case_id"]: row for row in rows}
    assert set(by_canonical) == {case["id"] for case in cases}
    assert set(synthesis["archetypes"]) == {case["archetype"] for case in cases}
    alias_count = 0
    for case in cases:
        row = by_canonical[case["id"]]
        assert row["case_id"] == case["id"]
        assert row["anchor_date"] == case["anchor_date"]
        assert row["archetype"] == case["archetype"]
        assert row["formal_causal_outcome"] == "UNMEASURED"
        assert row["witness"]
        for alias in row["aliases"]:
            alias_count += 1
            assert alias != case["id"]
            assert alias not in by_canonical
    assert alias_count == 3


def test_r10d_cites_fixture_id_and_aliases_stay_in_alias_arrays() -> None:
    fixture = _load(FIXTURE)
    synthesis = _load(SYNTHESIS)
    r10d = _load(R10D_JSON)
    rerating = (ROOT / R10D_MD).read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    rbi_ids = [case["id"] for case in fixture["cases"] if case["id"].startswith("R10-IN-RBI-")]
    assert rbi_ids == ["R10-IN-RBI-CONSUMER-CREDIT-RISKWEIGHTS-20231116"]
    rbi_id = rbi_ids[0]
    assert r10d["rbi"]["case_id"] == rbi_id
    assert f"`{rbi_id}`" in rerating
    r10d_text = json.dumps(r10d)
    for row in synthesis["cases"]:
        for alias in row["aliases"]:
            assert alias not in r10d_text
            assert alias not in rerating
            assert alias not in handoff


def test_r10_first_vertical_witnesses_resolve() -> None:
    packet = _load(PACKET)
    preflight = _load(R12)
    by_id = {record["record_id"]: record for record in packet["records"]}
    witnesses = preflight["first_vertical"]["witnesses"]
    assert len(witnesses) == 11
    for witness in witnesses:
        record = by_id[witness["record_id"]]
        assert witness["identity_binding_state"] == "RESEARCH_HINT_UNVALIDATED"
        assert record["identity_binding_state"] == "RESEARCH_HINT_UNVALIDATED"
        names = {record["ticker_hint"], *record.get("ticker_aliases", [])}
        assert witness["symbol"] in names
    bank = by_id["fin-research-bk-2025"]
    assert bank["ticker_hint"] == "BK"
    assert bank["ticker_aliases"] == ["BNY"]


def test_finance_handoff_names_finance_workstream() -> None:
    text = HANDOFF.read_text(encoding="utf-8")
    assert "WS:GMI-FINANCE-INTELLIGENCE" in text
    assert "No agentos workstream key exists" not in text
