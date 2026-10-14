"""Finance case falsifier — synthetic rows only.

The two rows live in tests/fixtures/finance_case_signal/synthesis_v0.json.
Nothing here reads research/finance.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from engine.sector_intelligence.finance_case_signal import (
    FinanceCaseSignalRefusal,
    project_falsifier,
)


_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "finance_case_signal"
    / "synthesis_v0.json"
)
_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "sector_intelligence"
    / "finance_intelligence_read_model.v1.schema.json"
)


def _document() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _row(canonical_case_id: str) -> dict:
    return next(
        row for row in _document()["cases"] if row["canonical_case_id"] == canonical_case_id
    )


def _falsifier_validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema["$defs"]["falsifier"])


def test_unmeasured_row_projects_not_yet_evaluable() -> None:
    row = _row("syn-fin-case-alpha")
    assert "MEASURED" in row["descriptive_evidence_state"]
    falsifier = project_falsifier(row)
    assert falsifier["state"] == "NOT_YET_EVALUABLE"
    assert falsifier["falsifier_id"] == row["canonical_case_id"]
    assert falsifier["statement"] == row["primary_limit"]
    assert falsifier["window"] == row["anchor_date"]
    _falsifier_validator().validate(falsifier)


def test_measured_outcome_is_refused() -> None:
    row = copy.deepcopy(_row("syn-fin-case-alpha"))
    row["formal_causal_outcome"] = "MEASURED"
    with pytest.raises(FinanceCaseSignalRefusal) as caught:
        project_falsifier(row)
    assert "WATCHING" not in str(caught.value)


def test_unknown_slice_is_refused() -> None:
    row = copy.deepcopy(_row("syn-fin-case-alpha"))
    row["slice_id"] = "not_a_finance_slice"
    with pytest.raises(FinanceCaseSignalRefusal):
        project_falsifier(row)


def test_alias_does_not_replace_canonical_id() -> None:
    row = _row("syn-fin-case-beta")
    alias = row["aliases"][0]
    falsifier = project_falsifier(row)
    assert falsifier["falsifier_id"] == row["canonical_case_id"]
    assert falsifier["falsifier_id"] != alias
