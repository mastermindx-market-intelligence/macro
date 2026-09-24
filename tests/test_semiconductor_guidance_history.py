"""T06 Semiconductor Theme Intelligence B: management-sequence assessment tests.

The owner-local projection over already-validated guidance/fact mappings must
project prior_outlook / actual / new_outlook into a closed assessment, refuse
unbridged comparisons explicitly, and surface derived midpoints ONLY when a
financial-owner receipt was supplied natively — never recompute arithmetic
itself.  These tests pin the frozen API from carrier PR #7870.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

from engine.company_intelligence import guidance_history
from engine.company_intelligence.guidance_history import (
    GuidanceHistoryError,
    SCHEMA,
    assess_management_sequence,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "semiconductor_theme_research"


def _load_case(name: str) -> dict:
    """Tiny local loader — the contract forbids importing tests/semiconductor_research_helpers.py."""
    payload = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert payload.get("synthetic") is True, f"fixture {name!r} must be synthetic"
    assert payload.get("status") == "ready", f"fixture {name!r} must be ready"
    assert "T06" in payload.get("task_refs", []), f"fixture {name!r} must reference T06"
    return payload


def _shape_prior_outlook(**overrides):
    base = {
        "schema": "guidance_item.v1",
        "metric": "revenue_usd_m",
        "low": 4150,
        "high": 4350,
        "unit": "USD_m",
        "horizon": "2026Q2",
        "status": "introduced",
        "basis": "reported_gaap",
        "currency": "USD",
        "perimeter": "as_reported",
        "definition": "revenue_net_of_returns",
        "source_span": {"synthetic": True, "document_id": "syn-doc-1", "locator": "paragraph 3"},
    }
    base.update(overrides)
    return base


def _shape_actual(**overrides):
    base = {
        "metric": "revenue_usd_m",
        "value": 4280,
        "unit": "USD_m",
        "fiscal_period": "2026Q2",
        "basis": "reported_gaap",
        "currency": "USD",
        "perimeter": "as_reported",
        "definition": "revenue_net_of_returns",
        "source_span": {"synthetic": True, "document_id": "syn-doc-2", "locator": "table 1 row 4"},
    }
    base.update(overrides)
    return base


def _shape_next_outlook(**overrides):
    base = {
        "schema": "guidance_item.v1",
        "metric": "revenue_usd_m",
        "low": 4500,
        "high": 4700,
        "unit": "USD_m",
        "horizon": "2026Q3",
        "status": "introduced",
        "basis": "reported_gaap",
        "currency": "USD",
        "perimeter": "as_reported",
        "definition": "revenue_net_of_returns",
        "source_span": {"synthetic": True, "document_id": "syn-doc-2", "locator": "paragraph 7"},
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Per-fixture regression coverage
# ─────────────────────────────────────────────────────────────────────────────


def test_perimeter_change_refuses_unbridged_delta():
    case = _load_case("guidance_perimeter_change")
    out = assess_management_sequence(**case["inputs"])
    assert out["schema"] == SCHEMA
    assert out["comparisons"]["prior_vs_actual"] == {
        "status": "refused",
        "reason": "perimeter_change",
        "position": None,
    }
    assert out["display"]["refused_deltas"] == ["prior_vs_actual"]
    # Roles still echo ALL values — refusal never hides source values.
    roles = out["roles"]
    assert roles["prior_outlook"]["perimeter"] == "organic"
    assert roles["actual"]["perimeter"] == "as_reported"
    assert roles["actual"]["value"] == 4380
    assert roles["prior_outlook"]["low"] == 4150
    assert roles["prior_outlook"]["high"] == 4350


def test_next_period_outlook_is_different_period():
    case = _load_case("guidance_next_period")
    out = assess_management_sequence(**case["inputs"])
    assert out["comparisons"]["prior_vs_actual"] == {
        "status": "comparable",
        "reason": None,
        "position": "within_range",
    }
    assert out["comparisons"]["actual_vs_new_outlook"] == {
        "status": "not_comparable",
        "reason": "different_period",
        "relationship": "next_outlook",
    }


def test_basis_change_variant_categorises_correctly():
    case = _load_case("guidance_basis_change")
    expected = case["expected_per_variant"]
    for variant_key, inputs in case["inputs_variants"].items():
        out = assess_management_sequence(**inputs)
        assert (
            out["comparisons"]["prior_vs_actual"]["reason"]
            == expected[variant_key]["comparisons"]["prior_vs_actual"]["reason"]
        ), f"variant {variant_key!r} reason mismatch"
        assert (
            out["comparisons"]["prior_vs_actual"]["status"]
            == "refused"
        ), f"variant {variant_key!r} must refuse"
        # fiscal period mismatch is checked first — see precedence test below.


def test_midpoint_unowned_when_no_derivations_supplied():
    case = _load_case("guidance_midpoint_unowned")
    variant = case["inputs_variants"]["no_native_derivations"]
    out = assess_management_sequence(**variant)
    assert out["derived"]["prior_midpoint"]["status"] == "unavailable"
    assert out["derived"]["prior_midpoint"]["reason"] == "derivation_unowned"
    assert out["derived"]["next_outlook_midpoint"]["status"] == "unavailable"
    assert out["derived"]["next_outlook_midpoint"]["reason"] == "derivation_unowned"


def test_midpoint_owned_only_uses_receipt_value_verbatim():
    case = _load_case("guidance_midpoint_unowned")
    variant = case["inputs_variants"]["prior_midpoint_owned_only"]
    out = assess_management_sequence(**variant)
    assert out["derived"]["prior_midpoint"]["status"] == "ready"
    # The module must not recompute or round — the value equals the receipt's
    # value verbatim.
    receipt_value = variant["native_derivations"]["prior_midpoint"]["value"]
    assert out["derived"]["prior_midpoint"]["value"] == receipt_value == 4243.5
    prior = variant["prior"]
    # Discriminating: the receipt value is deliberately NOT (low+high)/2, so a
    # module that recomputed the midpoint could not pass this assertion.
    assert out["derived"]["prior_midpoint"]["value"] != (prior["low"] + prior["high"]) / 2
    assert out["derived"]["next_outlook_midpoint"]["status"] == "unavailable"
    assert out["derived"]["next_outlook_midpoint"]["reason"] == "derivation_unowned"


# ─────────────────────────────────────────────────────────────────────────────
# No-midpoint-arithmetic guarantee
# ─────────────────────────────────────────────────────────────────────────────


def test_no_arithmetic_proof_module_does_not_compute_midpoint():
    """low=10, high=20 — if the module did (low+high)/2 it would emit 15.

    The actual value is set to 17 (NOT 15) so the literal "15" can only appear
    in the JSON dump if the module recomputed the midpoint from prior.low and
    prior.high.
    """
    prior = _shape_prior_outlook(low=10, high=20)
    actual = _shape_actual(value=17)
    next_outlook = _shape_next_outlook(low=30, high=40)
    out = assess_management_sequence(prior, actual, next_outlook)  # no native_derivations
    assert out["derived"]["prior_midpoint"]["status"] == "unavailable"
    assert out["derived"]["next_outlook_midpoint"]["status"] == "unavailable"
    assert "15" not in json.dumps(out), (
        "the literal '15' appearing anywhere in the JSON dump would imply the "
        "module computed (10+20)/2 = 15 (actual.value is 17, so 15 is only "
        "mintable by recomputing the midpoint)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Precedence order — first refusal reason wins
# ─────────────────────────────────────────────────────────────────────────────


def test_precedence_order_fiscal_period_mismatch_beats_basis_change():
    prior = _shape_prior_outlook(horizon="2026Q1", basis="reported_gaap")
    actual = _shape_actual(fiscal_period="2026Q2", basis="non_gaap")
    next_outlook = _shape_next_outlook(horizon="2026Q3")
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["reason"] == "fiscal_period_mismatch"


def test_precedence_metric_mismatch_beats_unit_mismatch():
    prior = _shape_prior_outlook(metric="revenue_usd_m", unit="USD_m")
    actual = _shape_actual(metric="eps", unit="USD_per_share")
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["reason"] == "metric_mismatch"


def test_precedence_unit_mismatch_after_metric_passes():
    prior = _shape_prior_outlook(metric="revenue_usd_m", unit="USD_m")
    actual = _shape_actual(metric="revenue_usd_m", unit="TWD_m")
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["reason"] == "unit_mismatch"


def test_precedence_basis_change_after_metric_unit_pass():
    prior = _shape_prior_outlook(basis="reported_gaap")
    actual = _shape_actual(basis="non_gaap")
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["reason"] == "basis_change"


def test_precedence_currency_mismatch_after_basis_passes():
    prior = _shape_prior_outlook(currency="USD")
    actual = _shape_actual(currency="TWD")
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["reason"] == "currency_mismatch"


def test_precedence_perimeter_change_after_currency_passes():
    prior = _shape_prior_outlook(perimeter="organic")
    actual = _shape_actual(perimeter="as_reported")
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["reason"] == "perimeter_change"


def test_precedence_definition_change_after_perimeter_passes():
    prior = _shape_prior_outlook(definition="revenue_gross")
    actual = _shape_actual(definition="revenue_net_of_returns")
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["reason"] == "definition_change"


def test_precedence_range_missing_when_low_or_high_missing():
    prior = _shape_prior_outlook(low=None)  # range missing
    actual = _shape_actual()
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["reason"] == "range_missing"


# ─────────────────────────────────────────────────────────────────────────────
# Position classification
# ─────────────────────────────────────────────────────────────────────────────


def test_position_within_range_when_value_equals_low():
    prior = _shape_prior_outlook(low=10, high=20)
    actual = _shape_actual(value=10)
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["position"] == "within_range"


def test_position_within_range_when_value_equals_high():
    prior = _shape_prior_outlook(low=10, high=20)
    actual = _shape_actual(value=20)
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["position"] == "within_range"


def test_position_above_range_when_value_exceeds_high():
    prior = _shape_prior_outlook(low=10, high=20)
    actual = _shape_actual(value=21)
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["position"] == "above_range"


def test_position_below_range_when_value_below_low():
    prior = _shape_prior_outlook(low=10, high=20)
    actual = _shape_actual(value=9)
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["comparisons"]["prior_vs_actual"]["position"] == "below_range"


# ─────────────────────────────────────────────────────────────────────────────
# Error contracts
# ─────────────────────────────────────────────────────────────────────────────


def test_new_outlook_same_period_raises():
    prior = _shape_prior_outlook(horizon="2026Q2")
    actual = _shape_actual(fiscal_period="2026Q2")
    next_outlook = _shape_next_outlook(horizon="2026Q2")
    with pytest.raises(GuidanceHistoryError) as exc:
        assess_management_sequence(prior, actual, next_outlook)
    assert str(exc.value) == "new_outlook_same_period"


def test_missing_key_raises_with_code():
    prior = _shape_prior_outlook()
    actual = {"metric": "x", "unit": "USD_m", "fiscal_period": "2026Q2", "source_span": {}}
    # missing 'value'
    next_outlook = _shape_next_outlook()
    with pytest.raises(GuidanceHistoryError) as exc:
        assess_management_sequence(prior, actual, next_outlook)
    assert str(exc.value) == "missing:actual.value"


def test_missing_prior_horizon_raises_with_code():
    prior = {"schema": "guidance_item.v1", "metric": "x", "low": 1, "high": 2, "unit": "u", "status": "s", "source_span": {}}
    actual = _shape_actual()
    next_outlook = _shape_next_outlook()
    with pytest.raises(GuidanceHistoryError) as exc:
        assess_management_sequence(prior, actual, next_outlook)
    assert str(exc.value) == "missing:prior.horizon"


def test_nan_value_raises_non_finite():
    prior = _shape_prior_outlook()
    actual = _shape_actual(value=float("nan"))
    next_outlook = _shape_next_outlook()
    with pytest.raises(GuidanceHistoryError) as exc:
        assess_management_sequence(prior, actual, next_outlook)
    assert str(exc.value) == "non_finite"


def test_infinity_value_raises_non_finite():
    prior = _shape_prior_outlook()
    actual = _shape_actual(value=float("inf"))
    next_outlook = _shape_next_outlook()
    with pytest.raises(GuidanceHistoryError) as exc:
        assess_management_sequence(prior, actual, next_outlook)
    assert str(exc.value) == "non_finite"


# ─────────────────────────────────────────────────────────────────────────────
# Closed output keys + literal authority
# ─────────────────────────────────────────────────────────────────────────────


def test_output_top_level_keys_are_closed():
    out = assess_management_sequence(
        _shape_prior_outlook(), _shape_actual(), _shape_next_outlook()
    )
    assert set(out.keys()) == {"schema", "roles", "comparisons", "derived", "display", "limitations", "authority"}


def test_roles_keys_are_closed():
    out = assess_management_sequence(
        _shape_prior_outlook(), _shape_actual(), _shape_next_outlook()
    )
    prior_keys = set(out["roles"]["prior_outlook"].keys())
    assert prior_keys == {
        "metric", "low", "high", "unit", "horizon", "status",
        "basis", "currency", "perimeter", "definition", "source_span",
    }
    actual_keys = set(out["roles"]["actual"].keys())
    assert actual_keys == {
        "metric", "value", "unit", "fiscal_period",
        "basis", "currency", "perimeter", "definition", "source_span",
    }


def test_authority_is_literal_all_false():
    out = assess_management_sequence(
        _shape_prior_outlook(), _shape_actual(), _shape_next_outlook()
    )
    assert out["authority"] == {
        "can_rank": False,
        "can_gate": False,
        "can_size": False,
        "can_originate": False,
        "can_open_entry": False,
    }


def test_limitations_include_no_external_consensus():
    out = assess_management_sequence(
        _shape_prior_outlook(), _shape_actual(), _shape_next_outlook()
    )
    assert "no_external_consensus" in out["limitations"]


def test_limitations_include_comparison_refused_reason_when_refused():
    prior = _shape_prior_outlook(perimeter="organic")
    actual = _shape_actual(perimeter="as_reported")
    next_outlook = _shape_next_outlook()
    out = assess_management_sequence(prior, actual, next_outlook)
    assert "comparison_refused:perimeter_change" in out["limitations"]


def test_comparisons_keys_are_closed():
    out = assess_management_sequence(
        _shape_prior_outlook(), _shape_actual(), _shape_next_outlook()
    )
    assert set(out["comparisons"].keys()) == {"prior_vs_actual", "actual_vs_new_outlook"}


# ─────────────────────────────────────────────────────────────────────────────
# source_span identity and non-mutation
# ─────────────────────────────────────────────────────────────────────────────


def test_source_span_passed_through_by_identity():
    prior_span = {"synthetic": True, "document_id": "syn-doc-1", "locator": "paragraph 3", "extra": {"a": 1}}
    actual_span = {"synthetic": True, "document_id": "syn-doc-2", "locator": "table 1 row 4"}
    next_span = {"synthetic": True, "document_id": "syn-doc-2", "locator": "paragraph 7"}
    prior = _shape_prior_outlook(source_span=prior_span)
    actual = _shape_actual(source_span=actual_span)
    next_outlook = _shape_next_outlook(source_span=next_span)
    out = assess_management_sequence(prior, actual, next_outlook)
    assert out["roles"]["prior_outlook"]["source_span"] == prior_span
    assert out["roles"]["actual"]["source_span"] == actual_span
    assert out["roles"]["new_outlook"]["source_span"] == next_span
    # never mutated
    assert prior_span == {"synthetic": True, "document_id": "syn-doc-1", "locator": "paragraph 3", "extra": {"a": 1}}
    assert actual_span == {"synthetic": True, "document_id": "syn-doc-2", "locator": "table 1 row 4"}
    assert next_span == {"synthetic": True, "document_id": "syn-doc-2", "locator": "paragraph 7"}


# ─────────────────────────────────────────────────────────────────────────────
# Import isolation — module imports nothing heavy / I/O-bound / off-package
# ─────────────────────────────────────────────────────────────────────────────


def test_module_imports_nothing_from_forbidden_paths():
    """Assert the module's source text and __dict__ carry no forbidden imports / I/O."""
    import inspect
    import re

    src = inspect.getsource(guidance_history)
    forbidden_substrings = (
        "import pandas",
        "from pandas",
        "import requests",
        "from requests",
        "import urllib",
        "from urllib",
        "import sqlalchemy",
        "from sqlalchemy",
        "open(",             # any file open()
        "os.environ",
        "json.load(",       # file-loading I/O (json.loads on already-parsed dicts is fine)
    )
    for needle in forbidden_substrings:
        assert needle not in src, f"guidance_history must not contain {needle!r}"
    # Forbidden package imports — matched as WORD-BOUNDARY package paths
    # (so e.g. "from typing import Any, Mapping" does not falsely match "app").
    forbidden_packages = (
        r"\bengine\.theme_graph\b",
        r"\bengine\.market_ontology\b",
        r"^app\b",        # bare "app" import (not substrings of typing.Mapping)
        r"^brain\b",
        r"\bengine\.scoring\b",
        r"\bengine\.rank\b",
        r"\bengine\.forecast\b",
    )
    # Build the actual import-statement lines present in the source:
    import_lines = [
        line.strip() for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        for pkg in forbidden_packages:
            if pkg.startswith(r"^"):
                # bare-name checks: the line must be the exact import
                assert not re.match(pkg, line), (
                    f"guidance_history import line {line!r} references forbidden package"
                )
            else:
                assert not re.search(pkg, line), (
                    f"guidance_history import line {line!r} references forbidden package {pkg!r}"
                )


def test_module_dict_has_no_open_or_pandas_attribute():
    assert not hasattr(guidance_history, "pandas"), "guidance_history must not bind pandas"
    # The module itself exposes only the FROZEN API names plus internal helpers.
    exposed = set(dir(guidance_history))
    required = {"assess_management_sequence", "GuidanceHistoryError", "SCHEMA"}
    assert required.issubset(exposed)

def test_non_finite_derivation_value_is_refused_not_displayed():
    import math
    import pytest
    case = _load_case("guidance_midpoint_unowned")
    variant = copy.deepcopy(case["inputs_variants"]["prior_midpoint_owned_only"])
    variant["native_derivations"]["prior_midpoint"]["value"] = math.nan
    with pytest.raises(GuidanceHistoryError, match="non_finite"):
        assess_management_sequence(**variant)


def _without_definitions(item):
    return {k: v for k, v in item.items() if k not in ("basis", "currency", "perimeter", "definition")}


def test_absent_on_both_sides_definitions_are_surfaced_as_unqualified_not_certified():
    """Matching unknowns do not certify comparability: when neither the prior
    outlook nor the actual states basis / currency / perimeter / definition the
    assessment still compares (frozen spec) but says definition_unqualified:<field>
    for each such field. A field stated on both sides is not flagged."""
    prior = _without_definitions(_shape_prior_outlook())
    actual = _without_definitions(_shape_actual())
    nxt = _without_definitions(_shape_next_outlook())
    out = assess_management_sequence(prior, actual, nxt)
    assert out["comparisons"]["prior_vs_actual"]["status"] != "refused"
    flagged = {entry for entry in out["limitations"] if entry.startswith("definition_unqualified:")}
    assert flagged == {"definition_unqualified:basis", "definition_unqualified:currency",
                       "definition_unqualified:perimeter", "definition_unqualified:definition"}
    stated = assess_management_sequence(
        {**prior, "basis": "reported_gaap", "currency": "USD"},
        {**actual, "basis": "reported_gaap", "currency": "USD"}, nxt)
    stated_flags = {entry for entry in stated["limitations"] if entry.startswith("definition_unqualified:")}
    assert stated_flags == {"definition_unqualified:perimeter", "definition_unqualified:definition"}
    assert "no_external_consensus" in stated["limitations"]


def test_fully_qualified_definitions_are_never_flagged_unqualified():
    out = assess_management_sequence(_shape_prior_outlook(), _shape_actual(), _shape_next_outlook())
    assert not [entry for entry in out["limitations"] if entry.startswith("definition_unqualified:")]


def test_prior_outlook_with_an_fx_assumption_surfaces_an_unreconciled_fx_limitation() -> None:
    prior = {**_shape_prior_outlook(), "fx_assumption": "1 US dollar to 32 NT dollars"}
    result = assess_management_sequence(prior, _shape_actual(), _shape_next_outlook())
    assert "fx_assumption_unreconciled" in result["limitations"]
    assert result["comparisons"]["prior_vs_actual"]["status"] in ("comparable", "refused")  # never a new refusal reason
    assert "fx_assumption" not in result["roles"]["prior_outlook"]  # frozen role echo unchanged
    plain = assess_management_sequence(_shape_prior_outlook(), _shape_actual(), _shape_next_outlook())
    assert "fx_assumption_unreconciled" not in plain["limitations"]

