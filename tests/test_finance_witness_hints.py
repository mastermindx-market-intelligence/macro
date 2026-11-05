"""Finance witness hint chips. Closed roster; no read of research/finance."""

from __future__ import annotations

import pytest

from engine.sector_intelligence.finance_projection import compose_finance_projection
from engine.sector_intelligence.finance_witness_hints import (
    FinanceWitnessHintRefusal,
    hint_binding,
)
from tests.test_finance_intelligence_projection import (
    _default_8slice_inputs,
    _default_operating_record,
    _knowledge_cutoff,
    _today,
)


def test_bny_hint_stays_unvalidated() -> None:
    binding = hint_binding("BNY")
    assert binding["state"] == "RESEARCH_HINT_UNVALIDATED"
    assert binding["record_id"] == "fin-research-bk-2025"
    assert binding["company_node_id"] is None
    assert binding["security_ref"] is None
    with pytest.raises(FinanceWitnessHintRefusal):
        hint_binding("BK")


# Plain strings transcribed from refs/grok/pr/7786 preflight witnesses
# (FINANCE_R12_INTEGRATION_PREFLIGHT_V0_1_2026-09-24.json lines 266-317).
# This test does not open that file. BNY keeps fin-research-bk-2025.
_PREFLIGHT_RECORD_IDS = {
    "V": "fin-research-v-2025",
    "MA": "fin-research-ma-2025",
    "FI": "fin-research-fi-2025",
    "FIS": "fin-research-fis-2025",
    "CME": "fin-research-cme-2025",
    "ICE": "fin-research-ice-2025",
    "NDAQ": "fin-research-ndaq-2025",
    "BNY": "fin-research-bk-2025",
    "STT": "fin-research-stt-2025",
    "SPGI": "fin-research-spgi-2025",
    "MCO": "fin-research-mco-2025",
}


def test_roster_record_ids_match_transcribed_preflight() -> None:
    observed = {
        symbol: hint_binding(symbol)["record_id"] for symbol in _PREFLIGHT_RECORD_IDS
    }
    assert observed == _PREFLIGHT_RECORD_IDS
    assert all(isinstance(record_id, str) for record_id in observed.values())
    with pytest.raises(FinanceWitnessHintRefusal):
        hint_binding("BK")


def test_hint_refuses_validated_upgrade() -> None:
    with pytest.raises(FinanceWitnessHintRefusal):
        hint_binding("BNY", state="IDENTITY_VALIDATED")


def test_unknown_symbol_is_refused() -> None:
    with pytest.raises(FinanceWitnessHintRefusal):
        hint_binding("GHOST")


def test_compose_paints_hint_without_a_stock_route() -> None:
    record = _default_operating_record(
        slice_id="card_networks",
        ticker="V",
        identity_state="IDENTITY_VALIDATED",
    )
    inputs = _default_8slice_inputs(
        identity_bindings={"V": hint_binding("V")},
        source_records=[record],
    )
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    rows = [row for row in document["company_exposures"] if row["ticker_hint"] == "V"]
    assert rows, "expected a V row"
    row = rows[0]
    assert row["identity"]["state"] == "RESEARCH_HINT_UNVALIDATED"
    assert row["company_route"]["href"] is None
    assert row["identity"]["company_node_id"] is None
    assert row["identity"]["security_ref"] is None
