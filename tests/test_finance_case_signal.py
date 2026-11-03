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
    _attach_falsifiers,
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
    assert str(caught.value) == "formal_causal_outcome_not_unmeasured"


def test_unknown_slice_is_refused() -> None:
    row = copy.deepcopy(_row("syn-fin-case-alpha"))
    row["slice_id"] = "not_a_finance_slice"
    with pytest.raises(FinanceCaseSignalRefusal) as caught:
        project_falsifier(row)
    assert str(caught.value) == "unknown_slice"


@pytest.mark.parametrize(
    ("field", "bad", "code"),
    [
        ("canonical_case_id", "", "missing_canonical_case_id"),
        ("canonical_case_id", None, "missing_canonical_case_id"),
        ("primary_limit", "", "missing_primary_limit"),
        ("primary_limit", None, "missing_primary_limit"),
        ("anchor_date", "", "missing_anchor_date"),
        ("anchor_date", None, "missing_anchor_date"),
    ],
    ids=lambda v: str(v),
)
def test_blank_or_absent_required_field_refuses_with_its_exact_code(field, bad, code) -> None:
    """An empty or None required field is refused with that field's missing_* code."""
    row = copy.deepcopy(_row("syn-fin-case-alpha"))
    row[field] = bad
    with pytest.raises(FinanceCaseSignalRefusal) as caught:
        project_falsifier(row)
    assert str(caught.value) == code


@pytest.mark.parametrize(
    "falsifier",
    [
        pytest.param(
            {"falsifier_id": "x", "statement": "s", "window": "w", "state": "WATCHING"},
            id="watching_state",
        ),
        pytest.param(
            {"falsifier_id": "y", "statement": "s", "state": "NOT_YET_EVALUABLE"},
            id="missing_window",
        ),
    ],
)
def test_attach_refuses_bad_falsifier_with_exact_code_and_leaves_slice_untouched(falsifier) -> None:
    """_attach_falsifiers refuses with an exact code and leaves the slice as it was.

    WATCHING is refused as watching_not_emitted; a falsifier without "window"
    is refused as invalid_falsifier. Neither write touches the slice doc.
    """
    expected = (
        "watching_not_emitted"
        if falsifier["state"] == "WATCHING"
        else "invalid_falsifier"
    )
    slice_doc = {
        "slice_id": "card_networks",
        "falsifiers": [{"falsifier_id": "kept", "statement": "old", "window": "w", "state": "WATCHING"}],
        "rerating": {"falsifier_ids": ["kept"]},
    }
    before = copy.deepcopy(slice_doc)
    with pytest.raises(FinanceCaseSignalRefusal) as caught:
        _attach_falsifiers(slice_doc, [falsifier])
    assert str(caught.value) == expected
    assert slice_doc == before


def test_alias_does_not_replace_canonical_id() -> None:
    row = _row("syn-fin-case-beta")
    alias = row["aliases"][0]
    falsifier = project_falsifier(row)
    assert falsifier["falsifier_id"] == row["canonical_case_id"]
    assert falsifier["falsifier_id"] != alias
