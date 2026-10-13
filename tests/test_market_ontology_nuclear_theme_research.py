"""Contract, registration, and envelope tests for the Nuclear vertical."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from jsonschema import FormatChecker

from engine.market_ontology import nuclear_theme_research as nuclear
from engine.theme_graph.curation_assertion import source_ref_for
from engine.market_ontology.theme_research_mounts import MountFacts
from engine.market_ontology.theme_research_registry import VerticalRegistration
from tests.nuclear_research_helpers import (
    N01, N02, N03, N03B, N04, N05, N06, N07, N08, N09, N10, N11, N12,
    X08, nuclear_bundle, nuclear_query,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "contracts/market_ontology/nuclear_theme_research.v1.schema.json").read_text())
EVIDENCE_CONTRACT_PATH = ROOT / "contracts/market_ontology/nuclear_theme_research.evidence.v1.schema.json"
ROBOTICS_PATH = ROOT / "contracts/market_ontology/robotics_theme_research.v1.schema.json"


def validate(payload):
    jsonschema.Draft202012Validator(CONTRACT, format_checker=FormatChecker()).validate(payload)


# One list for the schema validator and for nuclear._parse_day. The four
# impossible values are the ones $defs/when must refuse; the naive instant is
# a form _parse_day accepts and the schema must accept too.
WHEN_VALUES = (
    "2026-09-01",
    "2026-4-1",
    "2026-09-1",
    "2026-9-01",
    "2026-09- 1",
    "2024-02-29",
    "2000-02-29",
    "1900-02-28",
    "0001-01-01",
    "9999-12-31",
    "0004-02-29",
    "2024-2-29",
    "2026-02-31",
    "2026-02-29",
    "2026-13-45",
    "2026-00-01",
    "2026-01-00",
    "2026-04-31",
    "0000-01-01",
    "1900-02-29",
    "2026-01-32",
    "2026-09-01T00:00:00",
    "2026-09-01T00:00:00Z",
    "2026-09-01T00:00:00+00:00",
    "2026-09-01T00:00:00-05:30",
    "2026-09-01T00:00:00.1Z",
    "2026-09-01T00:00:00,5Z",
    "2026-09-01T00:00Z",
    "2026-09-01T00Z",
    "2026-09-01T23:59:59+23:59",
    "2024-02-29T00:00:00Z",
    "2024-02-29T00:00:00",
    "20260901T000000Z",
    "2026-09-01T000000Z",
    "0001-01-01T00:00:00Z",
    "9999-12-31T23:59:59Z",
    "2026-09-01T24:00:00Z",
    "2026-09-01T00:00:00+99:99",
    "2026-02-31T00:00:00Z",
    "2026-02-29T00:00:00",
    "2026-09-01T00:60:00Z",
    "2026-09-01T00:00:60Z",
    "2026-09-01T00:00:00+24:00",
    "2026-09-01T00:00:00-24:00",
    "2026-09-01T00:00:00z",
    "2026-4-1T00:00:00",
    "2026-13-01T00:00:00Z",
    "1900-02-29T00:00:00Z",
    "0000-01-01T00:00:00Z",
)
WHEN_REFUSED = (
    "2026-02-31",
    "2026-13-45",
    "2026-09-01T24:00:00Z",
    "2026-09-01T00:00:00+99:99",
)
_WHEN_VALIDATOR = jsonschema.Draft202012Validator(
    CONTRACT["$defs"]["when"], format_checker=FormatChecker())


def _parse_day_accepts(value):
    try:
        nuclear._parse_day(value)
    except ValueError:
        return False
    return True


@pytest.mark.parametrize("value", WHEN_VALUES)
def test_when_schema_matches_parse_day(value):
    """$defs/when agrees with nuclear_theme_research._parse_day on one list."""
    assert set(WHEN_REFUSED) <= set(WHEN_VALUES)
    accepted = _parse_day_accepts(value)
    errors = list(_WHEN_VALIDATOR.iter_errors(value))
    if value in WHEN_REFUSED:
        assert accepted is False
        assert errors
    assert (not errors) is accepted


def test_every_composed_payload_validates():
    payloads = [
        nuclear.compose_nuclear_research(
            nuclear_query("reactor_technology", view), nuclear_bundle(N01, N02, N03, N03B))
        for view in nuclear.VIEWS
    ] + [
        nuclear.compose_nuclear_research(
            nuclear_query("nuclear_components", view), nuclear_bundle(N04, N05, N06))
        for view in nuclear.VIEWS
    ] + [
        nuclear.compose_nuclear_research(
            nuclear_query("fuel_cycle", view), nuclear_bundle(N07, N08, N09, N10, N11, N12))
        for view in nuclear.VIEWS
    ] + [
        nuclear.compose_nuclear_research(
            nuclear_query("reactor_technology", "composition"), nuclear_bundle(X08))
    ]
    for payload in payloads:
        validate(payload)
    evidence_contract = json.loads(EVIDENCE_CONTRACT_PATH.read_text())
    evidence = nuclear.select_authorized_evidence(
        nuclear_query("nuclear_components", "economics"),
        nuclear_bundle(N04),
        source_ref_for(N04),
    )
    jsonschema.Draft202012Validator(
        evidence_contract, format_checker=FormatChecker()).validate(evidence)


def test_review_current_says_withheld_rows_are_absent_from_evidence_refs():
    description = (
        CONTRACT["$defs"]["industrial_row"]["properties"]["review"]["properties"]
        ["current"]["description"]
    )
    assert description == (
        "False exactly when a successor correction inside this selection "
        "supersedes the row; held, rejected, and expired rows are excluded "
        "from views and are absent from evidence_refs."
    )


def test_required_envelope_matches_shared_contracts():
    shared = json.loads((ROOT / "contracts/market_ontology/semiconductor_theme_research.v1.schema.json").read_text())
    assert CONTRACT["required"] == shared["required"]
    if ROBOTICS_PATH.exists():
        print("robotics contract read from disk")
        robotics = json.loads(ROBOTICS_PATH.read_text())
        assert CONTRACT["required"] == robotics["required"]
    else:
        print("robotics contract is not on this base; robotics required-list half skipped")


def test_constants_match_payload_and_authority_is_false():
    query = nuclear_query("nuclear_components", "economics")
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(N04, N05))
    assert payload["schema"] == nuclear.SCHEMA_ID == "nuclear_theme_research.v1"
    assert payload["definition_version"] == nuclear.DEFINITION_VERSION == "2026-09-25.1"
    assert nuclear.EVIDENCE_SCHEMA_ID == "nuclear_theme_research.evidence.v1"
    assert nuclear.ANCHOR_THEME_ID == "nuclear_power"
    assert set(payload["authority"].values()) == {False}


def test_nuclear_registration_entry_validates():
    def load_bundle(query, *, rights_snapshot=None):
        from engine.market_ontology.nuclear_owner_bundle import load_nuclear_owner_bundle
        return load_nuclear_owner_bundle(query, rights_snapshot=rights_snapshot)

    entry = VerticalRegistration(
        anchor_theme_id=nuclear.ANCHOR_THEME_ID,
        slice_keys=nuclear.SLICES,
        schema_id=nuclear.SCHEMA_ID,
        evidence_schema_id=nuclear.EVIDENCE_SCHEMA_ID,
        definition_version=nuclear.DEFINITION_VERSION,
        compose=nuclear.compose_nuclear_research,
        select_evidence=nuclear.select_authorized_evidence,
        load_bundle=load_bundle,
        title_en="Nuclear value capture",
        title_zh="核电价值捕获",
        note_en="This module reports public evidence without entry authority.",
        note_zh="该模块报告公开证据，不提供入场授权。",
    )
    mount = MountFacts(
        anchor_theme_id=nuclear.ANCHOR_THEME_ID,
        slice_keys=nuclear.SLICES,
        schema_id=nuclear.SCHEMA_ID,
        evidence_schema_id=nuclear.EVIDENCE_SCHEMA_ID,
        slice_labels={
            "reactor_technology": ("Reactor technology", "反应堆技术"),
            "nuclear_components": ("Nuclear components & services", "核电部件与服务"),
            "fuel_cycle": ("Fuel cycle — supplemental witnesses", "燃料循环——补充样本"),
        },
        title_en=entry.title_en,
        title_zh=entry.title_zh,
        note_en=entry.note_en,
        note_zh=entry.note_zh,
    )
    assert entry and mount
    assert nuclear.compose_nuclear_research.__module__ == "engine.market_ontology.nuclear_theme_research"
