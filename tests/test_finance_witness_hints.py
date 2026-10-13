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
