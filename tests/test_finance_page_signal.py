"""Page signal: admission writes each falsifier onto the slice with that slice_id.

The two rows live in tests/fixtures/finance_case_signal/synthesis_v0.json.
Nothing here reads research/finance. compose_finance_projection stays empty.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from engine.sector_intelligence.finance_page_signal import (
    SynthesisAdmissionRefusal,
    apply_page_signal,
)
from engine.sector_intelligence.finance_projection import compose_finance_projection
from tests.test_finance_intelligence_projection import (
    _default_8slice_inputs,
    _knowledge_cutoff,
    _today,
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


def _slice(slice_id: str, falsifier_id: str | None) -> dict:
    falsifiers = []
    ids: list[str] = []
    if falsifier_id is not None:
        falsifiers.append(
            {
                "falsifier_id": falsifier_id,
                "statement": "Previous statement.",
                "window": "2020-01-01",
                "state": "WATCHING",
            }
        )
        ids.append(falsifier_id)
    return {
        "slice_id": slice_id,
        "falsifiers": falsifiers,
        "rerating": {"falsifier_ids": ids},
    }


def _page() -> dict:
    return {
        "slices": [
            _slice("card_networks", "sentinel-card"),
            _slice("exchanges_trading_venues", None),
            _slice("custody_asset_servicing", "kept-id"),
        ]
    }


def _ids(page: dict) -> dict[str, list[str]]:
    return {
        sl["slice_id"]: [item["falsifier_id"] for item in sl["falsifiers"]]
        for sl in page["slices"]
    }


def test_admitted_row_lands_on_named_slice() -> None:
    case = _document()
    alpha = _row("syn-fin-case-alpha")
    beta = _row("syn-fin-case-beta")
    page = _page()
    apply_page_signal(case, page)
    by_id = {sl["slice_id"]: sl for sl in page["slices"]}
    card = by_id["card_networks"]
    placed = card["falsifiers"]
    assert len(placed) == 1
    falsifier = placed[0]
    assert falsifier["state"] == "NOT_YET_EVALUABLE"
    assert falsifier["falsifier_id"] == alpha["canonical_case_id"]
    assert falsifier["statement"] == alpha["primary_limit"]
    assert falsifier["window"] == alpha["anchor_date"]
    assert card["rerating"]["falsifier_ids"] == [falsifier["falsifier_id"]]
    _falsifier_validator().validate(falsifier)
    venue = by_id["exchanges_trading_venues"]
    assert venue["falsifiers"][0]["falsifier_id"] == beta["canonical_case_id"]
    assert venue["rerating"]["falsifier_ids"] == [beta["canonical_case_id"]]
    assert venue["falsifiers"][0]["state"] == "NOT_YET_EVALUABLE"
    kept = by_id["custody_asset_servicing"]
    assert [item["falsifier_id"] for item in kept["falsifiers"]] == ["kept-id"]
    assert kept["rerating"]["falsifier_ids"] == ["kept-id"]
    assert "WATCHING" not in {item["state"] for item in placed}


def test_measured_count_blocks_admission() -> None:
    case = _document()
    case["formal_causal_outcomes_measured"] = 1
    page = _page()
    before = _ids(page)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        apply_page_signal(case, page)
    assert str(caught.value) == "formal_causal_outcomes_measured"
    assert _ids(page) == before
    flat = [item for ids in _ids(page).values() for item in ids]
    assert "syn-fin-case-alpha" not in flat
    assert "syn-fin-case-beta" not in flat


def test_prospective_validation_blocks_admission() -> None:
    case = _document()
    case["prospective_validation_started"] = True
    page = _page()
    before = _ids(page)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        apply_page_signal(case, page)
    assert str(caught.value) == "prospective_validation_started"
    assert _ids(page) == before


def test_descriptive_measured_stays_not_yet_evaluable() -> None:
    alpha = _row("syn-fin-case-alpha")
    assert alpha["descriptive_evidence_state"] == "MARKET_AND_VALUATION_MEASURED"
    assert "MEASURED" in alpha["descriptive_evidence_state"]
    page = _page()
    apply_page_signal(_document(), page)
    card = next(sl for sl in page["slices"] if sl["slice_id"] == "card_networks")
    assert card["falsifiers"][0]["state"] == "NOT_YET_EVALUABLE"
    assert card["falsifiers"][0]["falsifier_id"] == alpha["canonical_case_id"]


def test_compose_keeps_empty_falsifiers() -> None:
    document = compose_finance_projection(
        _default_8slice_inputs(),
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    assert document["slices"]
    for sl in document["slices"]:
        assert sl["falsifiers"] == []
        assert sl["rerating"]["falsifier_ids"] == []
