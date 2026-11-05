"""Adversarial probes for the T04a Mining composition (frozen at c76aea66 — all FAIL).

One seat amendment after the freeze: R-MIN-32 re-bases BLOCKER-1 onto in-test packets
because its frozen premise about the casebook fixture was false. See that test's docstring.
"""
from __future__ import annotations
import dataclasses
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


def _mev_packet(pair, epe_value, la_value, unit):
    """R-MIN-31 §3 packet shape for one management-estimate-vs-actual comparison pair."""
    leg = lambda v: {
        "value": v,
        "unit": unit,
        "perimeter": "consolidated",
        "basis": "reported",
        "period": "Q2 2026",
    }
    return {
        "kind": "management_estimate_vs_actual",
        "pair": pair,
        "earlier_point_estimate": leg(epe_value),
        "later_actual": leg(la_value),
    }


def test_probe_blocker1_management_pair_is_actually_composed():
    """BLOCKER-1: the copper sales pair and its ONE ``pairs:`` cost pair must be surfaced.

    SEAT AMENDMENT (R-MIN-32, 2026-09-26). The probe as frozen drove this off
    ``synthetic_case("copper_complete")`` alone and asserted two comparison rows. That
    premise is false about the casebook: the copper fixture's ``economics`` block — the
    only thing ``mining_casebook.synthetic_case`` turns into a financial packet — is a
    REPORTED measure (``measure``/``value``/``basis``/``stream_threshold``), never an
    estimate-vs-actual pair. No comparison row can be composed from it without
    fabricating both legs, which is precisely the round-2 defect (leg ``value`` synthesised
    from ``period_kind``) this probe family exists to catch. The amendment supplies the two
    pairs the fixture never carried, keeps every original assertion (two distinct rows,
    comparison text present, ``is_range``/``is_consensus`` false) and ADDS the leg-value
    pins the frozen letter could be satisfied without: each leg must carry the literal
    numeric value from its packet, the two legs must differ, and no leg value may be a
    string. Intent preserved and strengthened; nothing relaxed.
    """
    case = synthetic_case("copper_complete")
    bundle = dataclasses.replace(
        case.bundle,
        financial_packets=(
            _mev_packet("sales", 1700, 1680, "Mlbs"),
            _mev_packet("unit_net_cash_cost", 1.55, 1.62, "USD/lb"),
        ),
    )
    result = composition.compose_mining_research(case.query, bundle)
    assert len(result["expectations"]) == 2, (
        "copper must surface the sales pair AND the one `pairs:` cost pair as a second "
        f"comparison; got {len(result['expectations'])}"
    )
    assert result["expectations"][0] is not result["expectations"][1]
    for row in result["expectations"]:
        assert row["is_range"] is False and row["is_consensus"] is False
        assert row["comparison"], "comparison text must be present on every pair"

    # Leg values are the packet's own numbers — never a re-used string from elsewhere in
    # the packet, and never equal across the two legs of one pair (round-2 regression pin).
    expected_legs = {
        1700: 1680,   # sales:              actual below the estimate
        1.55: 1.62,   # unit_net_cash_cost: actual above the estimate
    }
    seen = {}
    for row in result["expectations"]:
        epe = row["earlier_point_estimate"]["value"]
        la = row["later_actual"]["value"]
        for leg in (epe, la):
            assert isinstance(leg, (int, float)) and not isinstance(leg, bool), (
                f"leg value must be numeric, got {leg!r} ({type(leg).__name__})"
            )
        assert epe != la, f"a composed pair must carry two different leg values; got {epe!r} twice"
        assert epe in expected_legs, f"unexpected estimate leg {epe!r}"
        assert la == expected_legs[epe], (
            f"actual leg for estimate {epe!r} must be {expected_legs[epe]!r}; got {la!r}"
        )
        seen[epe] = la
    assert seen == expected_legs, f"both pairs must be composed exactly once; got {seen}"
    # Polarity follows the numbers, not the packet order.
    by_epe = {r["earlier_point_estimate"]["value"]: r["comparison"] for r in result["expectations"]}
    assert by_epe[1700] == "below_estimate", by_epe
    assert by_epe[1.55] == "above_estimate", by_epe


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
