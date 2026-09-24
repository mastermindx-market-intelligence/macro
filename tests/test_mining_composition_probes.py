"""Adversarial probes for the T04a Mining composition (frozen at c76aea66 — all FAIL)."""
from __future__ import annotations
import json
from pathlib import Path

import jsonschema
import pytest

from engine.market_ontology import mining_theme_research as composition
from tests.mining_casebook import CASE_NAMES, synthetic_case

SCHEMA = json.loads(
    (Path(__file__).parent.parent / "contracts" / "market_ontology"
     / "mining_theme_research.v1.schema.json").read_text(encoding="utf-8")
)
_V = jsonschema.Draft202012Validator(SCHEMA)


def test_probe_blocker1_management_pair_is_actually_composed():
    """BLOCKER-1: the copper sales pair and its ONE `pairs:` cost pair must be surfaced."""
    case = synthetic_case("copper_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert len(result["expectations"]) == 2, (
        "copper must surface the sales pair AND the one `pairs:` cost pair as a second "
        f"comparison; got {len(result['expectations'])}"
    )
    assert result["expectations"][0] is not result["expectations"][1]
    for row in result["expectations"]:
        assert row["is_range"] is False and row["is_consensus"] is False
        assert row["comparison"], "comparison text must be present on every pair"


def test_probe_blocker2_same_horizon_revision_emits_no_signed_block():
    """BLOCKER-2: a same-horizon management estimate is not reported economics."""
    case = synthetic_case("same_horizon_revision")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert result["economics"]["native_blocks"] == case.expected["signed_native_blocks"]


@pytest.mark.parametrize("name", CASE_NAMES)
def test_probe_blocker2b_native_blocks_match_the_frozen_casebook(name):
    """BLOCKER-2 (general): compose must agree with every case's frozen block expectation."""
    case = synthetic_case(name)
    result = composition.compose_mining_research(case.query, case.bundle)
    expected = case.expected["signed_native_blocks"]
    assert len(result["economics"]["native_blocks"]) == len(expected), name
    for got, want in zip(result["economics"]["native_blocks"], expected):
        assert got["value"] == want["value"] and got["measure"] == want["measure"]


@pytest.mark.parametrize("bad", [[{"free": "text", "number": 12345}], [12345], [None], [["x"]]])
def test_probe_blocker3_limitations_rejects_every_non_string(bad):
    """BLOCKER-3: `pattern` is vacuous for non-strings; the branch needs `type: string`."""
    case = synthetic_case("copper_complete")
    payload = composition.compose_mining_research(case.query, case.bundle)
    payload["limitations"] = bad
    with pytest.raises(jsonschema.ValidationError):
        _V.validate(payload)


def test_probe_major4_point_estimate_law_is_enforced_by_the_contract():
    """MAJOR-4: is_range/is_consensus must be required const false; comparison required non-empty."""
    item = SCHEMA["properties"]["expectations"]["items"]
    for key in ("is_range", "is_consensus", "comparison"):
        assert key in item["required"], f"{key} must be required on every expectations row"
    assert item["properties"]["is_range"].get("const") is False
    assert item["properties"]["is_consensus"].get("const") is False
    assert item["properties"]["comparison"].get("minLength", 0) >= 1


def test_probe_major4b_null_leg_requires_a_limitation():
    """MAJOR-4: an absent leg must not pass silently."""
    case = synthetic_case("copper_complete")
    payload = composition.compose_mining_research(case.query, case.bundle)
    payload["expectations"] = [{
        "stable_subject_id": "subject:x", "comparison_kind": "earlier_point_estimate_vs_later_actual",
        "earlier_point_estimate": None, "later_actual": None, "comparison": "",
        "is_range": True, "is_consensus": True,
    }]
    with pytest.raises(jsonschema.ValidationError):
        _V.validate(payload)


def test_probe_major5_definition_unqualified_uses_production_defined_fields():
    """MAJOR-5: the guard is inverted — an unqualified field must MINT the warning."""
    entry = [{"definition_unqualified_fields": ["basis", "unit", "perimeter"]}]
    out = composition._summarize_expectations(entry, defined_fields={"basis", "unit", "perimeter"})
    assert out["limitations"] == [
        "definition_unqualified:basis",
        "definition_unqualified:unit",
        "definition_unqualified:perimeter",
    ]


def test_probe_major8_ci_paths_cover_the_domain_file_read_at_import():
    """MAJOR-8: the module imports the domain md; the job must select on it."""
    ci = (Path(__file__).parent.parent / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    assert "research/mining/m1_integration_program/domain/" in ci


def test_probe_major9_native_blocks_bind_to_a_real_subject_identity():
    """MAJOR-9: ordering by stable source identity is degenerate while every id is the fallback."""
    case = synthetic_case("copper_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    ids = [b["stable_subject_id"] for b in result["economics"]["native_blocks"]]
    assert ids and all(i != "subject:unknown" for i in ids), ids
