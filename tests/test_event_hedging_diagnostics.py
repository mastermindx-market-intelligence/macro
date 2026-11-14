"""Synthetic mathematical/conformance evidence, not market validation."""
from copy import deepcopy

import pytest

from engine.event_hedging_diagnostics import (
    build_event_variance_diagnostic, compare_hedge_path_targets,
)
from engine.options_scenario_surface import build_hedge_target_change


@pytest.fixture
def variance_input():
    observed = {
        "security_id": "fixture:SPX", "window_start": "2026-10-08T18:00:00Z",
        "window_end": "2026-10-08T20:00:00Z", "variance_basis": "risk_neutral_integrated_variance",
        "unit": "return_decimal_squared", "return_basis": "log_return", "method_ref": "fixture:observed-method",
        "value": .0009, "source_ref": "fixture:observed", "source_revision": "v1",
        "observed_at": "2026-10-08T18:00:00Z", "known_at": "2026-10-08T18:00:01Z",
    }
    baseline = dict(observed, value=.0005, method_ref="fixture:baseline-model", source_ref="fixture:baseline")
    return dict(event_id="fixture:event", event_at="2026-10-08T18:15:00Z",
                event_known_at="2026-10-01T12:00:00Z", event_source_ref="fixture:schedule-v1",
                as_of="2026-10-08T18:00:02Z", observed=observed, counterfactual=baseline,
                calendar_complete=True, overlap_event_ids=[])


@pytest.fixture
def target_input():
    key = "SPXW:2026-10-08:C:6000"
    return dict(
        contracts=[dict(contract_id=key, option_root="SPXW", expiry="2026-10-08", right="C",
                        strike=6000., multiplier=100., iv=.20, settlement="PM", fixing_at="2026-10-08T20:00:00Z")],
        observed_at="2026-10-08T18:00:00Z", as_of="2026-10-08T18:00:02Z", spot=6000.,
        target_spot=5979., target_at="2026-10-08T18:20:00Z", iv_shift=.012,
        expected_contract_ids=[key], universe_ref="fixture:one-contract",
        source_receipt=dict(source_ref="fixture:source", source_revision="v1", contract_reference_revision="v1",
                            source_observed_at="2026-10-08T18:00:00Z", received_at="2026-10-08T18:00:01Z",
                            consumer_available_at="2026-10-08T18:00:02Z"),
        inventory=dict(scenario_id="fixture:path-inventory", evidence_class="SCENARIO",
                       starting={key: -100.}, ending={key: -100.}),
    )


def test_variance_units_and_counterfactual_identity(variance_input):
    original = deepcopy(variance_input)
    out = build_event_variance_diagnostic(**variance_input)
    assert out["excess_window_variance"] == pytest.approx(.0004)
    assert out["isolated_event_variance"] == pytest.approx(.0004)
    assert out["isolated_event_rms_move_pct"] == pytest.approx(2.)
    assert not any(out["authority"].values())
    assert variance_input == original
    assert build_event_variance_diagnostic(**variance_input) == out
    variance_input["counterfactual"]["source_revision"] = "corrected-v2"
    assert build_event_variance_diagnostic(**variance_input)["content_id"] != out["content_id"]


@pytest.mark.parametrize("calendar,overlap", [(None, None), (False, []), (True, None), (True, ["fixture:other"])])
def test_window_excess_is_not_isolated_event_without_overlap_evidence(variance_input, calendar, overlap):
    variance_input.update(calendar_complete=calendar, overlap_event_ids=overlap)
    out = build_event_variance_diagnostic(**variance_input)
    assert out["status"] == "available"
    assert out["excess_window_variance"] == pytest.approx(.0004)
    assert out["isolated_event_variance"] is None
    assert out["isolated_event_rms_move_pct"] is None
    assert out["attribution_reasons"]


def test_negative_residual_is_not_clipped(variance_input):
    variance_input["counterfactual"]["value"] = .001
    out = build_event_variance_diagnostic(**variance_input)
    assert out["excess_window_variance"] == pytest.approx(-.0001)
    assert out["residual_state"] == "baseline_exceeds_observed"
    assert out["isolated_event_rms_move_pct"] is None
    assert "negative_residual" in out["attribution_reasons"]


def test_measured_zero_is_preserved(variance_input):
    variance_input["counterfactual"]["value"] = .0009
    out = build_event_variance_diagnostic(**variance_input)
    assert out["excess_window_variance"] == 0
    assert out["isolated_event_rms_move_pct"] == 0


def test_atm_proxy_never_becomes_model_free_variance(variance_input):
    for key in ("observed", "counterfactual"):
        variance_input[key]["variance_basis"] = "atm_iv_squared_time_proxy"
    out = build_event_variance_diagnostic(**variance_input)
    assert out["inputs"]["observed"]["variance_basis"] == "atm_iv_squared_time_proxy"
    assert "proxy" in out["warnings"][1]


@pytest.mark.parametrize("field,value", [
    ("security_id", "different"), ("window_start", "2026-10-08T17:59:00Z"),
    ("window_end", "2026-10-08T21:00:00Z"), ("variance_basis", "atm_iv_squared_time_proxy"),
    ("return_basis", "simple_return"), ("unit", "vol_points"), ("known_at", "2026-10-08T18:00:03Z"),
    ("observed_at", "2026-10-08T18:00:02Z"), ("window_end", "2026-10-08T17:00:00Z"),
    ("source_ref", ""), ("value", True), ("value", None), ("value", float("nan")),
    ("value", float("inf")), ("value", -.1),
])
def test_variance_refuses_incomparable_invalid_or_future_evidence(variance_input, field, value):
    variance_input["counterfactual"][field] = value
    with pytest.raises(ValueError):
        build_event_variance_diagnostic(**variance_input)


@pytest.mark.parametrize("changes", [
    {"as_of": "2026-10-08T18:00:02"}, {"event_known_at": "2026-10-08T18:00:03Z"},
    {"event_at": "2026-10-08T18:00:00Z"}, {"event_at": "2026-10-08T21:00:00Z"},
    {"calendar_complete": 1}, {"overlap_event_ids": ["fixture:event"]},
    {"overlap_event_ids": ["a", "a"]}, {"overlap_event_ids": "a"},
    {"max_source_age_seconds": 0}, {"max_source_age_seconds": True},
])
def test_variance_event_boundary_validation(variance_input, changes):
    variance_input.update(changes)
    with pytest.raises(ValueError):
        build_event_variance_diagnostic(**variance_input)


def test_stale_variance_withholds_numbers(variance_input):
    variance_input["as_of"] = "2026-10-08T18:02:00Z"
    out = build_event_variance_diagnostic(**variance_input)
    assert out["status"] == "unavailable"
    assert out["excess_window_variance"] is None
    assert out["unavailable_reasons"] == ["stale_variance_evidence"]


def test_equivalent_offset_windows_are_comparable(variance_input):
    variance_input["counterfactual"]["window_start"] = "2026-10-08T14:00:00-04:00"
    variance_input["counterfactual"]["window_end"] = "2026-10-08T16:00:00-04:00"
    assert build_event_variance_diagnostic(**variance_input)["status"] == "available"


def _pair(args):
    a = build_hedge_target_change(**args)
    b = build_hedge_target_change(**dict(args, target_at="2026-10-08T18:45:00Z", target_spot=6020., iv_shift=-.02))
    return a, b


def test_remaining_hedge_uses_units_not_book_revaluation(target_input):
    a, b = _pair(target_input)
    originals = deepcopy((a, b))
    out = compare_hedge_path_targets(checkpoint=a, terminal=b, path_ref="fixture:path")
    expected = b["hedge"]["endpoint_target"] - a["hedge"]["endpoint_target"]
    assert out["status"] == "available"
    assert out["remaining_target_change"] == pytest.approx(expected)
    assert out["reference_notional_usd"] == pytest.approx(b["target_spot"] * expected)
    wrong = b["hedge"]["reference_notional_usd"] - a["hedge"]["reference_notional_usd"]
    assert out["reference_notional_usd"] != pytest.approx(wrong)
    assert out["actual_exhaustion_probability"] is None
    assert not any(out["authority"].values())
    assert (a, b) == originals
    assert compare_hedge_path_targets(checkpoint=a, terminal=b, path_ref="fixture:path") == out


def test_tampered_result_is_refused(target_input):
    a, b = _pair(target_input)
    a["hedge"]["target_change"] += 1
    with pytest.raises(ValueError, match="identity mismatch"):
        compare_hedge_path_targets(checkpoint=a, terminal=b, path_ref="fixture:path")


@pytest.mark.parametrize("change", ["source", "anchor_inventory", "universe", "pricing", "inventory_id"])
def test_cross_anchor_comparisons_are_unavailable(target_input, change):
    a, _ = _pair(target_input)
    changed = deepcopy(target_input)
    changed.update(target_at="2026-10-08T18:45:00Z", target_spot=6020.)
    key = changed["expected_contract_ids"][0]
    if change == "source":
        changed["source_receipt"]["source_revision"] = "v2"
    elif change == "anchor_inventory":
        changed["inventory"]["starting"][key] = -90.
    elif change == "universe":
        changed["universe_ref"] = "fixture:different"
    elif change == "pricing":
        changed["r"] = .01
    else:
        changed["inventory"]["scenario_id"] = "different-inventory"
    b = build_hedge_target_change(**changed)
    out = compare_hedge_path_targets(checkpoint=a, terminal=b, path_ref="fixture:path")
    assert out["status"] == "unavailable"
    assert out["remaining_target_change"] is None
    assert out["reference_notional_usd"] is None


def test_incomplete_endpoint_is_not_zero(target_input):
    a, _ = _pair(target_input)
    b = build_hedge_target_change(**dict(target_input, target_at="2026-10-08T20:00:00Z"))
    assert b["hedge"] is None
    out = compare_hedge_path_targets(checkpoint=a, terminal=b, path_ref="fixture:path")
    assert out["remaining_target_change"] is None
    assert "incomplete_scenario_endpoint" in out["unavailable_reasons"]


def test_unordered_endpoints_are_not_a_path(target_input):
    a, b = _pair(target_input)
    out = compare_hedge_path_targets(checkpoint=b, terminal=a, path_ref="fixture:path")
    assert out["remaining_direction"] == "unavailable"
    assert "unordered_scenario_endpoints" in out["unavailable_reasons"]


def test_path_reference_participates_in_identity(target_input):
    a, b = _pair(target_input)
    left = compare_hedge_path_targets(checkpoint=a, terminal=b, path_ref="fixture:path-a")
    right = compare_hedge_path_targets(checkpoint=a, terminal=b, path_ref="fixture:path-b")
    assert left["content_id"] != right["content_id"]
