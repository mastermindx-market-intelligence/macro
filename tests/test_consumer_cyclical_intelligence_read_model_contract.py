"""Contract tests for consumer_cyclical_intelligence_read_model.v1.

The contract is the authority for the Consumer Cyclical V1-CORE economic-change
read model. These tests pin the guarantees the projection is allowed to rely on:
the committed fixture validates, the contract is discoverable by the shared
sector-intelligence registry, and the closed shapes actually reject the things
they are meant to reject.

Boundary context: research/consumer_cyclical/v1/V1_PLNT_BOUNDARY_AND_FROZEN_SPEC.md
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ID = "consumer_cyclical_intelligence_read_model.v1"
SCHEMA_PATH = (
    ROOT / "contracts" / "sector_intelligence" / f"{CONTRACT_ID}.schema.json"
)
FIXTURE_PATH = (
    ROOT / "data" / "sector_intelligence" / "fixtures" / f"{CONTRACT_ID}.valid.json"
)


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text())


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text())


def _validator():
    return jsonschema.Draft202012Validator(_schema())


def _errors(document: Any) -> list[Any]:
    return sorted(_validator().iter_errors(document), key=lambda e: list(e.path))


def test_committed_fixture_validates() -> None:
    errors = _errors(_fixture())
    assert errors == [], [(list(e.path), e.message) for e in errors[:5]]


def test_contract_is_discoverable_by_the_shared_registry() -> None:
    """The shared registry resolves contracts by properties.contract_id.const.

    tests/test_sector_intelligence_contracts.py asserts every schema file under
    contracts/sector_intelligence/ is discoverable this way, so a contract that
    omits it silently breaks the whole family's enumeration.
    """
    schema = _schema()
    assert schema["properties"]["contract_id"]["const"] == CONTRACT_ID
    assert schema["contract_id"]["const"] == CONTRACT_ID
    assert schema["$id"].endswith(f"sector_intelligence/{CONTRACT_ID}.schema.json")


def test_fixture_encodes_the_r6_golden_oracle() -> None:
    """R6 section 7.1, USD thousands. The -4 residual must survive."""
    emitted = {r["key"]: r["value_text"] for r in _fixture()["results"]}
    assert emitted["total_revenue_change"] == "24344"
    assert emitted["advertising_revenue_change"] == "10141"
    assert emitted["advertising_expense_change"] == "10145"
    assert emitted["advertising_net_change"] == "-4"
    assert emitted["advertising_current_period_net"] == "0"
    assert emitted["advertising_share_of_revenue_change_pct"] == "41.66"
    # The two advertising changes are NOT equal at displayed precision.
    assert (
        emitted["advertising_revenue_change"]
        != emitted["advertising_expense_change"]
    )


def test_source_acceptance_clock_is_never_labelled() -> None:
    """R6 section 4: the SEC acceptance string carries no timezone.

    Never attach Z, and never treat it as first public availability.
    """
    for record in _fixture()["source_records"]:
        raw = record.get("sec_acceptance_raw")
        if raw is None:
            continue
        assert not raw.endswith("Z"), raw
        assert "+" not in raw, raw


def test_value_text_supplied_as_a_number_is_rejected() -> None:
    doc = _fixture()
    doc["facts"][0]["value_text"] = 365223
    assert _errors(doc)


def test_fact_missing_evidence_revision_is_rejected() -> None:
    doc = _fixture()
    doc["facts"][0]["evidence"].pop("revision", None)
    assert _errors(doc)


def test_unknown_top_level_property_is_rejected() -> None:
    doc = _fixture()
    doc["unexpected_plane"] = {"anything": True}
    assert _errors(doc)


def test_unknown_key_inside_a_result_is_rejected() -> None:
    """$defs/result is closed — this is what keeps value_decimal out."""
    doc = _fixture()
    doc["results"][0]["value_decimal"] = "24344"
    assert _errors(doc)


@pytest.mark.parametrize("field", ["ranking", "position_size", "entry", "score"])
def test_explanation_cannot_express_ranking_or_sizing_authority(field: str) -> None:
    """R15: the explanatory panel carries no ranking/entry/gating/sizing authority."""
    doc = _fixture()
    doc["explanation"][field] = "anything"
    assert _errors(doc), field


def test_a_result_must_bind_at_least_one_input_ref() -> None:
    doc = _fixture()
    doc["results"][0]["input_refs"] = []
    assert _errors(doc)


def test_a_ready_document_must_carry_facts_and_at_least_one_unwithheld_result() -> None:
    doc = _fixture()
    assert doc["availability"] == "ready"
    empty = copy.deepcopy(doc)
    empty["facts"] = []
    assert _errors(empty), "ready document with no facts must be rejected"
    withheld = copy.deepcopy(doc)
    for result in withheld["results"]:
        result["value_text"] = None
        result["withheld_reason"] = "denominator_nonpositive"
    assert _errors(withheld), "ready document with no unwithheld result must be rejected"


def test_an_unavailable_document_with_no_facts_is_valid() -> None:
    """R15: zero ready results renders as unavailable — never empty-ready."""
    doc = _fixture()
    doc["availability"] = "unavailable"
    doc["facts"] = []
    doc["results"] = []
    doc["degraded_dependencies"] = [
        {"dependency": "total_revenue_change", "reason": "inputs_absent", "state": "unavailable"}
    ]
    assert _errors(doc) == []


def test_degraded_dependency_shape_is_closed() -> None:
    doc = _fixture()
    doc["degraded_dependencies"] = [
        {"fact_key": "total_revenue", "reason": "missing", "state": "unavailable"}
    ]
    assert _errors(doc)
