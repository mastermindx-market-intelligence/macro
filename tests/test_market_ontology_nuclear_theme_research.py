"""Contract, registration, and envelope tests for the Nuclear vertical."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from jsonschema import FormatChecker

from engine.market_ontology import nuclear_theme_research as nuclear
from engine.market_ontology.theme_research_mounts import MountFacts
from engine.market_ontology.theme_research_registry import VerticalRegistration
from tests.nuclear_research_helpers import (
    N01, N02, N03, N03B, N04, N05, N06, N07, N08, N09, N10, N11, N12,
    X08, nuclear_bundle, nuclear_query,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "contracts/market_ontology/nuclear_theme_research.v1.schema.json").read_text())
ROBOTICS_PATH = ROOT / "contracts/market_ontology/robotics_theme_research.v1.schema.json"


def validate(payload):
    jsonschema.Draft202012Validator(CONTRACT, format_checker=FormatChecker()).validate(payload)


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
