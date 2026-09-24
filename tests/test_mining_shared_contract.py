import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.market_ontology.mining_dependency_binding import (
    RESULT_KEYS,
    MiningResearchRefusal,
    publication_harness,
    validate_delivery_inputs,
)
from tests.mining_casebook import CASE_NAMES, synthetic_case

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mining_economic_dossier"
AUTHORITY_FLAGS = {
    "can_rank": False,
    "can_gate": False,
    "can_size": False,
    "can_originate": False,
    "can_open_entry": False,
}


def test_case_names_are_closed_and_unknown_name_lists_every_known_name():
    assert CASE_NAMES == (
        "copper_complete",
        "rare_earth_complete",
        "missing_basis",
        "missing_issuer",
        "source_only",
        "missing_stream_threshold",
        "changed_source",
        "signed_loss",
        "same_horizon_revision",
        "denied_source",
        "page_generation_change",
    )
    with pytest.raises(KeyError) as raised:
        synthetic_case("not-a-mining-case")
    assert str(raised.value) == (
        "\"unknown case 'not-a-mining-case'; known: " + ", ".join(CASE_NAMES) + "\""
    )


@pytest.mark.parametrize("name", CASE_NAMES)
def test_every_fixture_is_synthetic_and_all_authority_flags_are_false(name):
    case = synthetic_case(name)
    fixture = json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))
    assert fixture["synthetic"] is True
    assert fixture["authority"] == AUTHORITY_FLAGS
    assert case.query.expected_generation == case.account_generation
    assert set(case.expected) == {"signed_native_blocks", "reported_only_economics"}
    assert case.bundle.native_refs[0]["url"].startswith("https://example.invalid/")
    assert "0000831259" not in fixture["issuer"].get("cik", "")
    assert "0001801368" not in fixture["issuer"].get("cik", "")


def test_loader_refuses_a_fixture_that_is_not_synthetic(tmp_path, monkeypatch):
    fixture = tmp_path / "copper_complete.json"
    fixture.write_text('{"synthetic": false}', encoding="utf-8")
    monkeypatch.setattr("tests.mining_casebook._fixture_path", lambda name: fixture)
    with pytest.raises(ValueError, match="not marked synthetic"):
        synthetic_case("copper_complete")


@pytest.mark.parametrize(
    "name, usable",
    [
        ("copper_complete", True),
        ("rare_earth_complete", True),
        ("missing_basis", False),
        ("missing_issuer", False),
        ("source_only", False),
        ("missing_stream_threshold", False),
        ("changed_source", False),
        ("signed_loss", False),
        ("same_horizon_revision", False),
        ("denied_source", False),
        ("page_generation_change", False),
    ],
)
def test_delivery_validation_refuses_live_admission_for_every_case(name, usable):
    case = synthetic_case(name)
    result = validate_delivery_inputs(
        {
            "query": case.query,
            "bundle": case.bundle,
            "expected": case.expected,
            "account_generation": case.account_generation,
        }
    )
    assert tuple(result) == RESULT_KEYS
    assert result["live_admission"] == "refused"
    assert result["research_usable"] is usable
    assert isinstance(result["reasons"], list)
    assert all(reason == "" or reason.endswith(".") for reason in result["reasons"])


def test_delivery_validation_has_a_closed_input_contract():
    case = synthetic_case("copper_complete")
    with pytest.raises(ValueError, match="unexpected delivery input keys"):
        validate_delivery_inputs(
            {
                "query": case.query,
                "bundle": case.bundle,
                "expected": case.expected,
                "account_generation": case.account_generation,
                "extra": True,
            }
        )


@pytest.mark.parametrize(
    "override, code",
    [
        ({"slice_key": "unknown_slice"}, "unknown_slice"),
        ({"anchor_theme_id": "theme:rare_earth_critical_min"}, "slice_theme_mismatch"),
        ({"limit": True}, "limit_out_of_range"),
        ({"limit": 0}, "limit_out_of_range"),
        ({"offset": True}, "offset_negative"),
        ({"offset": -1}, "offset_negative"),
        ({"expected_generation": None}, "expected_generation_required"),
        ({"source_cutoff": None}, "replay_cutoffs_required"),
        ({"recorded_cutoff": None}, "replay_cutoffs_required"),
        ({"expected_generation": "different-generation"}, "generation_changed"),
    ],
)
def test_mining_owns_typed_query_refusals(override, code):
    case = synthetic_case("copper_complete")
    query = replace(case.query, **override)
    with pytest.raises(MiningResearchRefusal) as raised:
        validate_delivery_inputs(
            {
                "query": query,
                "bundle": case.bundle,
                "expected": case.expected,
                "account_generation": case.account_generation,
            }
        )
    assert raised.value.code == code


def test_shared_contract_is_probed_lazily_and_degrades_to_a_typed_refusal():
    case = synthetic_case("copper_complete")
    with pytest.raises(MiningResearchRefusal) as raised:
        publication_harness().client(entitled=True)
    assert raised.value.code == "shared_contract_unavailable"


def test_route_unbound_refusal_is_identical_for_entitled_and_unentitled_callers():
    refusal = publication_harness().client(entitled=False)
    assert refusal.code == "route_unbound"
    assert refusal.read_count == 0
    assert refusal.detail == (
        "The shared paths /api/themes/v1/research/query and "
        "/api/themes/v1/research/evidence are absent on main."
    )
    entitled = publication_harness().client(entitled=True)
    assert entitled == refusal


def test_casebook_does_not_import_the_semiconductor_module():
    source = Path(__file__).with_name("mining_casebook.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "engine.market_ontology.semiconductor_theme_research" not in modules
