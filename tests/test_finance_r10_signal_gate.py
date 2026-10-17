"""Review gate: a descriptive MEASURED state never becomes a cause.

The fixture is the two-row synthetic file shared with FIN-1. This module
calls that projector and does not read a research/finance path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.sector_intelligence.finance_case_signal import project_falsifier
from engine.sector_intelligence.finance_page_signal import (
    SynthesisAdmissionRefusal,
    admit_synthesis,
)


_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "finance_case_signal"
    / "synthesis_v0.json"
)


def _document() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _measured_descriptive_row(document: dict) -> dict:
    return next(
        row
        for row in document["cases"]
        if row["descriptive_evidence_state"] == "MARKET_AND_VALUATION_MEASURED"
    )


def test_fixture_outcomes_stay_unmeasured() -> None:
    document = _document()
    assert document["formal_causal_outcomes_measured"] == 0
    assert document["prospective_validation_started"] is False
    assert all(row["formal_causal_outcome"] == "UNMEASURED" for row in document["cases"])
    row = _measured_descriptive_row(document)
    assert "MEASURED" in row["descriptive_evidence_state"]
    falsifier = project_falsifier(row)
    assert falsifier["state"] == "NOT_YET_EVALUABLE"
    admitted = admit_synthesis(document)
    match = next(item for item in admitted if item["falsifier_id"] == row["canonical_case_id"])
    assert match["state"] == "NOT_YET_EVALUABLE"


def test_measured_count_blocks_admission() -> None:
    document = _document()
    document["formal_causal_outcomes_measured"] = 1
    with pytest.raises(SynthesisAdmissionRefusal):
        admit_synthesis(document)


def test_alias_row_keeps_canonical_case_id() -> None:
    document = _document()
    row = next(item for item in document["cases"] if item["aliases"])
    alias = row["aliases"][0]
    falsifier = project_falsifier(row)
    assert falsifier["falsifier_id"] == row["canonical_case_id"]
    assert falsifier["falsifier_id"] != alias
