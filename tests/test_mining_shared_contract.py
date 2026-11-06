import ast
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from engine.market_ontology.mining_dependency_binding import (
    OMISSION_REASONS,
    OMISSION_TO_LIMITATION,
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
        "\"unknown case 'not-a-mining-case'; known: copper_complete, rare_earth_complete, "
        "missing_basis, missing_issuer, source_only, missing_stream_threshold, changed_source, "
        "signed_loss, same_horizon_revision, denied_source, page_generation_change\""
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
    issuer = fixture.get("issuer") or {}
    assert issuer.get("fictional", True) is True
    assert "0000831259" not in issuer.get("cik", "")
    assert "0001801368" not in issuer.get("cik", "")


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
        ("signed_loss", True),
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
    assert all(reason.endswith(".") for reason in result["reasons"])


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
        ({"offset": 1, "expected_generation": None}, "expected_generation_required"),
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


def test_shared_contract_is_probed_lazily_and_is_two_armed_on_the_unmerged_base():
    # R-MIN-26: never a skip. Absent base -> the typed refusal; present base (#7870 merged) ->
    # a callable comes back. Either arm is a real assertion.
    harness = publication_harness()
    if importlib.util.find_spec("engine.theme_graph.curation_assertion") is None:
        with pytest.raises(MiningResearchRefusal) as raised:
            harness.shared_contract()
        assert raised.value.code == "shared_contract_unavailable"
    else:
        assert callable(harness.shared_contract())
    assert harness.read_count == 0


def test_shared_contract_degrade_is_typed_when_the_import_itself_fails(monkeypatch):
    monkeypatch.setitem(sys.modules, "engine.theme_graph.curation_assertion", None)
    with pytest.raises(MiningResearchRefusal) as raised:
        publication_harness().shared_contract()
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


REPO_ROOT = Path(__file__).resolve().parents[1]
MINING_SOURCES = (
    "tests/mining_casebook.py",
    "tests/test_mining_shared_contract.py",
    "tests/test_mining_shared_contract_probes.py",
    "engine/market_ontology/mining_dependency_binding.py",
)


@pytest.mark.parametrize("relative", MINING_SOURCES)
def test_mining_code_and_tests_never_import_the_semiconductor_module(relative):
    # R-MIN-24: forbidden in Mining code AND Mining tests, in every import spelling.
    tree = ast.parse((REPO_ROOT / relative).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert not any(name.startswith("engine.market_ontology.semiconductor_theme_research") for name in imported), imported


EXPECTED_SHAPE = {
    # case -> (signed native blocks, reported-only economics) — hand-written, not derived.
    "copper_complete": (1, 0),
    "rare_earth_complete": (1, 0),
    "missing_basis": (0, 1),
    "missing_issuer": (0, 1),
    "source_only": (0, 1),
    "missing_stream_threshold": (0, 1),
    "changed_source": (0, 1),
    "signed_loss": (1, 0),
    "same_horizon_revision": (0, 1),
    "denied_source": (0, 1),
    "page_generation_change": (0, 1),
}


@pytest.mark.parametrize("name, shape", sorted(EXPECTED_SHAPE.items()))
def test_expected_oracle_shape_is_pinned_per_case(name, shape):
    case = synthetic_case(name)
    assert (len(case.expected["signed_native_blocks"]), len(case.expected["reported_only_economics"])) == shape
    if name == "signed_loss":
        block = case.expected["signed_native_blocks"][0]
        assert block["value"] < 0 and block["sign_preserved"] is True
        assert case.bundle.omissions == ()


def test_expected_oracle_is_read_and_cross_checked_against_omissions():
    case = synthetic_case("source_only")
    contradicting = {
        "signed_native_blocks": [{"measure": "fictional operating income", "value": 111, "basis": "fictional reported dollars"}],
        "reported_only_economics": [],
    }
    with pytest.raises(ValueError, match="expected contradicts omissions"):
        validate_delivery_inputs(
            {"query": case.query, "bundle": case.bundle, "expected": contradicting, "account_generation": case.account_generation}
        )
    with pytest.raises(ValueError, match="expected must carry exactly"):
        validate_delivery_inputs(
            {"query": case.query, "bundle": case.bundle, "expected": {"signed_native_blocks": []}, "account_generation": case.account_generation}
        )


def test_an_undeclared_account_generation_mismatch_in_the_revision_tuple_is_refused():
    case = synthetic_case("page_generation_change")
    assert dict(case.bundle.revision_tuple)["account_generation"] != case.account_generation
    assert "page_generation" in case.bundle.omissions
    undeclared = replace(case.bundle, omissions=())
    with pytest.raises(ValueError, match="without the page_generation omission"):
        validate_delivery_inputs(
            {"query": case.query, "bundle": undeclared, "expected": case.expected, "account_generation": case.account_generation}
        )


T04_LIMITATIONS = {
    "missing_derivation",
    "stream_threshold_unknown",
    "missing_basis",
    "source_only",
    "missing_issuer",
    "changed_source",
    "denied_source",
    "page_generation_change",
    "industry_total_unknown",
}


def test_omission_words_map_onto_the_t04_limitation_vocabulary_without_overlap():
    assert set(OMISSION_TO_LIMITATION) == set(OMISSION_REASONS)
    assert set(OMISSION_REASONS) & T04_LIMITATIONS == set()
    assert set(OMISSION_TO_LIMITATION.values()) <= T04_LIMITATIONS
    assert "positive_witness" not in OMISSION_REASONS  # a signed loss is a block, not an omission (R-MIN-30)
    for word in OMISSION_REASONS:
        assert not word.startswith("definition_unqualified:")
        assert word not in {"missing_derivation", "stream_threshold_unknown"}


def test_route_unbound_reports_the_harness_read_counter():
    harness = publication_harness()
    assert harness.client().read_count == 0
    harness.read_count = 2
    assert harness.client().read_count == 2
