"""Conditional price x future-time options surface — R2 scenario-field contract."""
from __future__ import annotations

import copy
import importlib
import importlib.util
import json
import math
from datetime import datetime, timedelta, timezone
import subprocess
import sys

import numpy as np
import pytest

from engine.intraday_greeks import bs_greeks_vec, bs_price, compute_greek_grids
from engine.options_scenario_surface import (
    PRODUCT_KIND,
    SCHEMA,
    _zero_crossings,
    build_scenario_surface,
)

OBS = "2026-09-18T14:00:00.123456Z"
SPOT = 100.0


def _endpoint_inputs():
    return {
        "contracts": [{
            "contract_id": "SPXW:2026-10-08:C:6000", "option_root": "SPXW",
            "expiry": "2026-10-08", "right": "C", "strike": 6000.0,
            "multiplier": 100.0, "iv": 0.20, "settlement": "PM",
            "fixing_at": "2026-10-08T20:00:00Z",
        }],
        "observed_at": "2026-10-08T18:00:00Z", "as_of": "2026-10-08T18:00:02Z",
        "spot": 6000.0, "target_spot": 5979.0,
        "target_at": "2026-10-08T18:20:00Z", "iv_shift": 0.012,
        "expected_contract_ids": ["SPXW:2026-10-08:C:6000"],
        "universe_ref": "fixture:complete-one-contract-book",
        "source_receipt": {
            "source_ref": "fixture:source-1", "source_observed_at": "2026-10-08T18:00:00Z",
            "received_at": "2026-10-08T18:00:01Z",
            "consumer_available_at": "2026-10-08T18:00:02Z",
        },
        "inventory": {
            "scenario_id": "fixture:short-call", "evidence_class": "SCENARIO",
            "starting": {"SPXW:2026-10-08:C:6000": -100.0},
            "ending": {"SPXW:2026-10-08:C:6000": -110.0},
        },
    }


def _endpoint(**changes):
    from engine import options_scenario_surface as owner
    assert hasattr(owner, "build_hedge_target_change"), "missing incumbent endpoint repricing seam"
    kwargs = _endpoint_inputs()
    kwargs.update(changes)
    return owner.build_hedge_target_change(**kwargs)


def test_endpoint_reprices_book_and_does_not_trade_existing_hedge_revaluation():
    out = _endpoint()
    delta0 = float(bs_greeks_vec(6000., 6000., 120 / (365 * 1440), .2, True)[0])
    delta1 = float(bs_greeks_vec(5979., 6000., 100 / (365 * 1440), .212, True)[0])
    b0, b1 = 10000 * delta0, 11000 * delta1
    assert out["hedge"]["target_change"] == pytest.approx(b1 - b0)
    assert out["hedge"]["reference_notional_usd"] == pytest.approx(5979 * (b1 - b0))
    assert out["hedge"]["reference_notional_usd"] != pytest.approx(5979 * b1 - 6000 * b0)
    assert out["attribution"]["repricing"] + out["attribution"]["inventory"] == pytest.approx(b1 - b0)
    assert out["evidence_class"] == "SCENARIO"
    assert out["authority"]["calibrated_probability"] is False
    assert out["coverage"]["scope"] == "supplied_universe"


@pytest.mark.parametrize("field,value", [
    ("consumer_available_at", "2026-10-08T18:00:03Z"),
    ("received_at", "2026-10-08T18:00:03Z"),
    ("source_observed_at", "2026-10-08T18:01:00Z"),
    ("consumer_available_at", None),
])
def test_endpoint_rejects_late_or_unknown_availability(field, value):
    receipt = _endpoint_inputs()["source_receipt"]
    receipt[field] = value
    with pytest.raises(ValueError):
        _endpoint(source_receipt=receipt)


def test_endpoint_missing_contract_and_fixing_crossing_are_unavailable_not_zero():
    missing = _endpoint(expected_contract_ids=["SPXW:2026-10-08:C:6000", "missing"])
    assert missing["status"] == "unavailable"
    assert missing["hedge"] is None
    fixed = _endpoint(target_at="2026-10-08T20:00:00Z")
    assert fixed["status"] == "unavailable"
    assert "fixing_boundary" in fixed["unavailable_reasons"]


def test_inventory_scenario_uses_qualified_flow_once_and_preserves_unknown():
    from engine import options_scenario_surface as owner
    assert hasattr(owner, "build_inventory_scenario"), "missing deterministic inventory seam"
    out = owner.build_inventory_scenario(
        {"c": -10, "p": 20}, {"c": 8, "p": -6},
        dealer_fraction=.5, scenario_id="half-participation",
    )
    assert out["ending"] == {"c": -14, "p": 23}
    assert out["evidence_class"] == "SCENARIO"
    with pytest.raises(ValueError):
        owner.build_inventory_scenario({"c": None}, {"c": 0}, dealer_fraction=.5, scenario_id="unknown")


@pytest.mark.parametrize("seconds", [1, 60, 300, 900, 1800, 3599, 3600, 3601])
@pytest.mark.parametrize("right", ["C", "P"])
def test_endpoint_exact_final_hour_matches_independent_erf_delta(seconds, right):
    args = _endpoint_inputs()
    row = args["contracts"][0]
    row["right"] = right
    # Same endpoint spot/time with a position increment isolates exact-time delta.
    anchor = datetime(2026, 10, 8, 20, tzinfo=timezone.utc) - timedelta(seconds=seconds)
    args.update(observed_at=anchor.isoformat(), as_of=anchor.isoformat(),
                target_at=anchor.isoformat(), target_spot=6000.1, spot=6000.1, iv_shift=0., r=0., q=0.)
    args["source_receipt"].update({k: anchor.isoformat() for k in
                                ["source_observed_at", "received_at", "consumer_available_at"]})
    args["inventory"]["starting"][row["contract_id"]] = 0.
    args["inventory"]["ending"][row["contract_id"]] = 1.
    from engine.options_scenario_surface import build_hedge_target_change
    out = build_hedge_target_change(**args)
    t = seconds / (365 * 86400)
    d1 = (math.log(6000.1 / 6000) + .5 * .2**2 * t) / (.2 * math.sqrt(t))
    independent = .5 * (1 + math.erf(d1 / math.sqrt(2))) - (right == "P")
    assert out["hedge"]["target_change"] == pytest.approx(-100 * independent, abs=1e-5)


@pytest.mark.parametrize("position", [-100., 0., 100.])
def test_endpoint_unchanged_state_is_zero_for_either_inventory_sign(position):
    inv = _endpoint_inputs()["inventory"]
    inv["starting"] = inv["ending"] = {"SPXW:2026-10-08:C:6000": position}
    out = _endpoint(inventory=inv, target_at="2026-10-08T18:00:00Z", target_spot=6000., iv_shift=0.)
    assert out["hedge"]["target_change"] == 0
    assert out["hedge"]["reference_notional_usd"] == 0


def test_endpoint_missing_inventory_cannot_be_an_empty_position():
    inv = _endpoint_inputs()["inventory"]
    inv["ending"] = {}
    out = _endpoint(inventory=inv)
    assert out["hedge"] is None
    assert "unknown_inventory" in out["unavailable_reasons"]


def test_endpoint_scope_and_identity_preserve_all_expiry_denominator():
    args = _endpoint_inputs()
    other = dict(args["contracts"][0], contract_id="later", expiry="2026-10-09",
                 fixing_at="2026-10-09T20:00:00Z")
    args["contracts"].append(other)
    args["expected_contract_ids"].append("later")
    args["inventory"]["starting"]["later"] = 50
    args["inventory"]["ending"]["later"] = 50
    from engine.options_scenario_surface import build_hedge_target_change
    all_exp = build_hedge_target_change(**args)
    args["contracts"].reverse()
    args["expected_contract_ids"].reverse()
    assert build_hedge_target_change(**args)["content_id"] == all_exp["content_id"]
    selected = build_hedge_target_change(**args, expiry_scope=["2026-10-08"])
    assert selected["coverage"]["selected"] == 1
    assert selected["coverage"]["received"] == 2
    assert selected["content_id"] != all_exp["content_id"]
    assert selected["hedge"]["target_change"] == pytest.approx(_endpoint()["hedge"]["target_change"])
    assert sum(x["target_change"] for x in all_exp["by_expiry"]) == pytest.approx(all_exp["hedge"]["target_change"])


@pytest.mark.parametrize("field,value", [("iv", None), ("iv", float("nan")), ("iv", True)])
def test_endpoint_invalid_iv_is_unavailable(field, value):
    rows = _endpoint_inputs()["contracts"]
    rows[0][field] = value
    out = _endpoint(contracts=rows)
    assert out["hedge"] is None
    assert "invalid_iv" in out["unavailable_reasons"]
    json.dumps(out, allow_nan=False)


def test_endpoint_rejects_duplicate_economic_identity_and_nonstandard_deliverable():
    args = _endpoint_inputs()
    args["contracts"].append(dict(args["contracts"][0], contract_id="alias"))
    args["expected_contract_ids"].append("alias")
    with pytest.raises(ValueError, match="economic"):
        _endpoint(contracts=args["contracts"], expected_contract_ids=args["expected_contract_ids"])
    row = _endpoint_inputs()["contracts"][0]
    row["multiplier"] = 10
    with pytest.raises(ValueError, match="deliverable"):
        _endpoint(contracts=[row])


def test_endpoint_stale_source_and_invalid_target_iv_never_emit_hedge():
    assert "stale_source" in _endpoint(as_of="2026-10-08T18:02:00Z")["unavailable_reasons"]
    assert "invalid_target_iv" in _endpoint(iv_shift=-.2)["unavailable_reasons"]


def test_endpoint_existing_cli_supports_same_pure_contract(tmp_path):
    src = tmp_path / "book.json"
    src.write_text(json.dumps(_endpoint_inputs()))
    proc = subprocess.run([sys.executable, "scripts/build_options_scenario_surface.py",
                           "--mode", "hedge-target", "--input", str(src)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == _endpoint()


def test_endpoint_path_net_telescopes_but_does_not_claim_turnover():
    from engine.options_scenario_surface import build_hedge_target_change
    a = _endpoint_inputs()
    b = copy.deepcopy(a)
    b.update(observed_at=a["target_at"], as_of=a["target_at"], spot=a["target_spot"],
             target_at="2026-10-08T18:40:00Z", target_spot=6010., iv_shift=-.012)
    b["contracts"][0]["iv"] += a["iv_shift"]
    b["inventory"]["starting"] = dict(a["inventory"]["ending"])
    b["inventory"]["ending"] = dict(a["inventory"]["starting"])
    b["source_receipt"].update({k: b["observed_at"] for k in
                                ["source_observed_at", "received_at", "consumer_available_at"]})
    direct = copy.deepcopy(a)
    direct.update(target_at=b["target_at"], target_spot=b["target_spot"], iv_shift=0.)
    direct["inventory"]["ending"] = dict(b["inventory"]["ending"])
    qa = build_hedge_target_change(**a)["hedge"]["target_change"]
    qb = build_hedge_target_change(**b)["hedge"]["target_change"]
    qdirect = build_hedge_target_change(**direct)["hedge"]["target_change"]
    assert qa + qb == pytest.approx(qdirect)
    assert abs(qa) + abs(qb) > abs(qdirect)


def test_endpoint_near_cancellation_retains_gross_and_symmetric_inventory_identity():
    args = _endpoint_inputs()
    row = dict(args["contracts"][0], contract_id="put", right="P")
    args["contracts"].append(row)
    args["expected_contract_ids"].append("put")
    args["inventory"]["starting"]["put"] = 100.
    args["inventory"]["ending"]["put"] = 110.
    from engine.options_scenario_surface import build_hedge_target_change
    out = build_hedge_target_change(**args, q=0.)
    assert out["hedge"]["target_change"] == pytest.approx(1000.)
    assert out["hedge"]["gross_contract_target_changes"] > 1000.
    assert 0 < out["hedge"]["cancellation_ratio"] < 1
    assert out["attribution"]["identity_residual"] == pytest.approx(0., abs=1e-10)


def test_endpoint_overflow_refuses_numeric_result_instead_of_serializing_infinity():
    inv = _endpoint_inputs()["inventory"]
    inv["ending"]["SPXW:2026-10-08:C:6000"] = 1e308
    out = _endpoint(inventory=inv)
    assert out["hedge"] is None
    assert "nonfinite_repricing" in out["unavailable_reasons"]
    json.dumps(out, allow_nan=False)


def test_inventory_scenario_rejects_partial_flow_or_authority_claim():
    from engine.options_scenario_surface import build_inventory_scenario
    with pytest.raises(ValueError, match="universe"):
        build_inventory_scenario({"c": 1, "p": 1}, {"c": 0}, dealer_fraction=0, scenario_id="zero")
    inv = _endpoint_inputs()["inventory"]
    inv["evidence_class"] = "OBSERVED"
    with pytest.raises(ValueError, match="SCENARIO"):
        _endpoint(inventory=inv)


def test_conditioned_inventory_assumptions_survive_endpoint_and_cannot_be_tampered():
    from engine.options_scenario_surface import build_inventory_scenario
    key = "SPXW:2026-10-08:C:6000"
    inv = build_inventory_scenario({key: -100}, {key: 20}, dealer_fraction=.5, scenario_id="half")
    out = _endpoint(inventory=inv)
    assert out["inventory_assumptions"]["dealer_fraction"] == .5
    assert out["inventory_assumptions"]["signed_flow"][key] == 20
    inv["ending"][key] = -120
    with pytest.raises(ValueError, match="conditioned inventory"):
        _endpoint(inventory=inv)


def test_endpoint_cli_rejects_duplicate_json_members(tmp_path):
    src = tmp_path / "ambiguous.json"
    raw = json.dumps(_endpoint_inputs())
    src.write_text(raw[:-1] + ',"target_spot":1234}')
    proc = subprocess.run([sys.executable, "scripts/build_options_scenario_surface.py",
                           "--mode", "hedge-target", "--input", str(src)], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "duplicate JSON member" in proc.stderr


def test_inventory_nontrade_adjustment_is_separate_and_never_signed_as_flow():
    from engine.options_scenario_surface import build_inventory_scenario
    key = "SPXW:2026-10-08:C:6000"
    inv = build_inventory_scenario({key: -100}, {key: 20}, dealer_fraction=.5,
                                  scenario_id="adjusted", nontrade_adjustments={key: 7})
    assert inv["trade_increment"][key] == -10
    assert inv["nontrade_adjustments"][key] == 7
    assert inv["ending"][key] == -103
    out = _endpoint(inventory=inv)
    plain = _endpoint_inputs()["inventory"]
    plain["ending"][key] = -103
    assert out["hedge"] == _endpoint(inventory=plain)["hedge"]
    assert out["inventory_assumptions"]["nontrade_assumption"] == "supplied"
    # Changing the adjustment without changing the endpoint is detectable.
    inv["nontrade_adjustments"][key] = 8
    with pytest.raises(ValueError, match="conditioned inventory"):
        _endpoint(inventory=inv)


@pytest.mark.parametrize("adjustments", [{}, {"c": None}, {"c": 0, "alien": 0}])
def test_inventory_partial_unknown_adjustments_are_not_assumed_zero(adjustments):
    from engine.options_scenario_surface import build_inventory_scenario
    with pytest.raises(ValueError):
        build_inventory_scenario({"c": -10}, {"c": 0}, dealer_fraction=.5,
                                 scenario_id="adjusted", nontrade_adjustments=adjustments)


def test_inventory_omitted_adjustments_are_an_explicit_scenario_assumption():
    from engine.options_scenario_surface import build_inventory_scenario
    inv = build_inventory_scenario({"c": -10}, {"c": 0}, dealer_fraction=.5, scenario_id="fixed")
    assert inv["nontrade_assumption"] == "assumed_zero"
    assert inv["nontrade_adjustments"] == {"c": 0.}


def test_endpoint_contract_specific_iv_is_repriced_per_leg_not_averaged():
    from engine.options_scenario_surface import build_hedge_target_change
    args = _endpoint_inputs()
    key = args["contracts"][0]["contract_id"]
    args["contracts"].append(dict(args["contracts"][0], contract_id="put", right="P"))
    args["expected_contract_ids"].append("put")
    args["inventory"]["starting"]["put"] = 50
    args["inventory"]["ending"]["put"] = 60
    args.update(iv_shift=0., target_iv_by_contract={key: .3, "put": .15})
    before = copy.deepcopy(args)
    out = build_hedge_target_change(**args)
    initial = bs_greeks_vec(6000., np.array([6000., 6000.]), 120/(365*1440),
                            .2, np.array([True, False]))[0]
    endpoint = bs_greeks_vec(5979., np.array([6000., 6000.]), 100/(365*1440),
                             np.array([.3, .15]), np.array([True, False]))[0]
    expected = sum(-100 * (np.array([-110, 60]) * endpoint - np.array([-100, 50]) * initial))
    assert out["hedge"]["target_change"] == pytest.approx(expected)
    assert out["assumptions"]["vol_map"] == "supplied_contract_endpoint_iv"
    assert {r["contract_id"]: r["target_iv"] for r in out["contracts"]} == args["target_iv_by_contract"]
    assert args == before


def test_endpoint_iv_surface_requires_explicit_universe_and_unambiguous_shock():
    key = _endpoint_inputs()["contracts"][0]["contract_id"]
    with pytest.raises(ValueError, match="universe"):
        _endpoint(iv_shift=0., target_iv_by_contract={})
    with pytest.raises(ValueError, match="iv_shift"):
        _endpoint(iv_shift=.01, target_iv_by_contract={key: .3})
    for invalid in (None, -1, True, float("nan"), float("inf")):
        out = _endpoint(iv_shift=0., target_iv_by_contract={key: invalid})
        assert out["hedge"] is None
        assert "invalid_target_iv" in out["unavailable_reasons"]
        json.dumps(out, allow_nan=False)


def test_endpoint_cohorts_reconcile_at_anchor_and_keep_missing_book_unavailable():
    from engine.options_scenario_surface import build_hedge_target_change
    args = _endpoint_inputs()
    for days in (1, 7, 8):
        expiry = (datetime(2026, 10, 8) + timedelta(days=days)).date().isoformat()
        key = f"day-{days}"
        args["contracts"].append(dict(args["contracts"][0], contract_id=key,
                                    expiry=expiry, fixing_at=expiry + "T20:00:00Z"))
        args["expected_contract_ids"].append(key)
        args["inventory"]["starting"][key] = days * 10
        args["inventory"]["ending"][key] = days * 10
    out = build_hedge_target_change(**args)
    assert {r["cohort"]: r["contracts"] for r in out["by_cohort"]} == {"0DTE": 1, "1-7D": 2, "8+D": 1}
    assert sum(r["target_change"] for r in out["by_cohort"]) == pytest.approx(out["hedge"]["target_change"])
    args["contracts"].pop()
    incomplete = build_hedge_target_change(**args)
    assert incomplete["hedge"] is None
    assert incomplete["by_cohort"] == []


def test_endpoint_cohort_migration_uses_new_york_dates_not_utc_or_time_fraction():
    args = _endpoint_inputs()
    key = args["contracts"][0]["contract_id"]
    args["contracts"][0].update(expiry="2026-10-16", fixing_at="2026-10-16T20:00:00Z")
    # UTC has already reached Oct 9, but New York is still Oct 8 at the anchor.
    args.update(observed_at="2026-10-09T01:30:00Z", as_of="2026-10-09T01:30:00Z",
                target_at="2026-10-09T05:00:00Z")
    args["source_receipt"].update({k: args["observed_at"] for k in
                                ("source_observed_at", "received_at", "consumer_available_at")})
    from engine.options_scenario_surface import build_hedge_target_change
    out = build_hedge_target_change(**args)
    assert out["cohort_migrations"] == [{"contract_id": key, "from": "8+D", "to": "1-7D"}]
    assert next(r for r in out["by_cohort"] if r["cohort"] == "8+D")["target_change"] == out["hedge"]["target_change"]


def test_endpoint_source_revision_changes_identity_without_backdating_or_repricing():
    args = _endpoint_inputs()
    args["source_receipt"].update(source_revision="revision-1", contract_reference_revision="reference-3")
    before = _endpoint(**args)
    args["source_receipt"]["source_revision"] = "revision-2"
    after = _endpoint(**args)
    assert before["content_id"] != after["content_id"]
    assert before["hedge"] == after["hedge"]
    assert after["source_receipt"]["source_revision"] == "revision-2"
    assert after["source_receipt"]["contract_reference_revision"] == "reference-3"
    assert _endpoint()["source_receipt"]["source_revision"] is None
    assert all(after["authority"][flag] is False for flag in ("ranking", "portfolio", "sizing", "auto_exit"))


def _contracts():
    rows = []
    for strike in (90.0, 95.0, 100.0, 105.0, 110.0):
        rows.append({
            "strike": strike,
            "exp_years": 1.0 / 365.0,
            "iv": 0.22,
            "oi": 2200.0 if strike >= 100 else 200.0,
            "right": "C",
            "expiry": "2026-09-19",
        })
        rows.append({
            "strike": strike,
            "exp_years": 1.0 / 365.0,
            "iv": 0.22,
            "oi": 2200.0 if strike < 100 else 200.0,
            "right": "P",
            "expiry": "2026-09-19",
        })
    return rows


def _build(contracts=None, **kwargs):
    params = {
        "root": "SPY",
        "observed_at": OBS,
        "spot": SPOT,
        "price_grid": [90, 95, 100, 105, 110],
        "horizons_minutes": [0, 60, 24 * 60],
    }
    params.update(kwargs)
    return build_scenario_surface(contracts if contracts is not None else _contracts(), **params)


def test_scenario_surface_builder_is_a_distinct_additive_engine():
    spec = importlib.util.find_spec("engine.options_scenario_surface")
    assert spec is not None, "conditional scenario surface engine does not exist"
    module = importlib.import_module("engine.options_scenario_surface")
    assert callable(module.build_scenario_surface)


def test_payload_is_explicitly_scenario_not_observed_history_or_forecast():
    out = _build()
    assert out["schema"] == SCHEMA == "options.scenario_surface/v1"
    assert out["product_kind"] == PRODUCT_KIND == "conditional_price_time_scenario"
    assert out["assumptions"]["observed_history"] is False
    assert out["assumptions"]["price_axis"] == "scenario_not_forecast"
    assert out["assumptions"]["inventory"] == "fixed_input_oi_snapshot"
    assert out["assumptions"]["vol_map"] == "sticky_strike"
    assert out["observed_at"] == OBS
    assert any("not observed history" in w for w in out["warnings"])
    assert any("not a predicted path" in w for w in out["warnings"])
    assert out["source_clocks"] == {
        "market_observed_at": OBS,
        "iv_observed_at": None,
        "oi_vintage": None,
        "trade_at_first": None,
        "trade_at_last": None,
        "quote_at_first": None,
        "quote_at_last": None,
    }
    assert out["conventions"]["contract_multiplier"] == 100.0
    assert out["conventions"]["pct_move"] == 0.01


def test_source_clock_provenance_is_explicit_and_never_inherited():
    iv_clock = "2026-09-18T13:59:58.900000Z"
    out = _build(oi_vintage="2026-09-17", iv_observed_at=iv_clock)
    assert out["source_clocks"]["market_observed_at"] == OBS
    assert out["source_clocks"]["iv_observed_at"] == iv_clock
    assert out["source_clocks"]["oi_vintage"] == "2026-09-17"


def test_horizon_zero_reuses_incumbent_greek_kernel_and_exposure_convention():
    contracts = _contracts()
    out = _build(contracts, price_grid=[99, 100, 101], horizons_minutes=[0])
    K = np.asarray([c["strike"] for c in contracts], float)
    T = np.asarray([c["exp_years"] for c in contracts], float)
    iv = np.asarray([c["iv"] for c in contracts], float)
    oi = np.asarray([c["oi"] for c in contracts], float)
    calls = np.asarray([c["right"] == "C" for c in contracts], bool)
    sign = np.where(calls, 1.0, -1.0)
    _, gamma, vanna, charm = bs_greeks_vec(100.0, K, T, iv, calls)
    expected_g = float(np.sum(sign * gamma * oi * 100.0 * 100.0 * 100.0 * 0.01))
    expected_v = float(np.sum(sign * vanna * oi * 100.0 * 100.0 * 0.01))
    expected_c = float(np.sum(sign * (charm / 365.0) * oi * 100.0 * 100.0))
    assert out["grids"]["gex"][0][1] == pytest.approx(expected_g)
    assert out["grids"]["vex"][0][1] == pytest.approx(expected_v)
    assert out["grids"]["cex"][0][1] == pytest.approx(expected_c)


def test_time_roll_forward_excludes_expired_contracts_and_preserves_missingness():
    contracts = _contracts()
    out = _build(
        contracts,
        price_grid=[95, 100, 105],
        horizons_minutes=[0, 12 * 60, 24 * 60, 24 * 60 + 1],
    )
    assert out["horizon_meta"][0]["active_contracts"] == len(contracts)
    assert out["horizon_meta"][1]["active_contracts"] == len(contracts)
    assert out["horizon_meta"][2]["active_contracts"] == 0
    assert out["grids"]["gex"][2] == [None, None, None]
    assert out["grids"]["vex"][3] == [None, None, None]
    assert out["horizon_meta"][2]["active_snapshot_fraction"] == 0.0
    assert out["grids"]["cex"][0] != out["grids"]["cex"][1]


def test_expiry_scope_and_max_dte_are_applied_to_the_frozen_snapshot():
    contracts = _contracts()
    contracts.append({
        "strike": 100.0,
        "exp_years": 30.0 / 365.0,
        "iv": 0.30,
        "oi": 9999.0,
        "right": "C",
        "expiry": "2026-10-18",
    })
    out = _build(
        contracts,
        horizons_minutes=[0],
        expiry_scope=["2026-09-19"],
        max_dte_days=7,
    )
    assert out["source_counts"]["input"] == len(contracts)
    assert out["source_counts"]["valid_snapshot"] == len(contracts) - 1
    assert out["source_counts"]["omitted_scope"] == 1
    assert out["expiry_scope"] == ["2026-09-19"]


def test_multiple_gamma_zeros_are_retained_not_collapsed_to_nearest_crossing():
    xs = [80.0, 90.0, 100.0, 110.0, 120.0]
    ys = [-3.0, 2.0, -1.0, 4.0, -2.0]
    zeros = _zero_crossings(xs, ys)
    assert len(zeros) == 4
    assert zeros == sorted(zeros)
    assert all(80.0 < x < 120.0 for x in zeros)


def test_selected_metric_zero_contours_are_emitted_for_gamma_vanna_and_charm():
    out = _build(price_grid=[85, 90, 95, 100, 105, 110, 115], horizons_minutes=[0, 60])
    assert set(out["zero_crossings"]) == {"gex", "vex", "cex"}
    for metric in ("gex", "vex", "cex"):
        rows = out["zero_crossings"][metric]
        assert [row["horizon_minutes"] for row in rows] == [0, 60]
        for idx, row in enumerate(rows):
            assert row["prices"] == _zero_crossings(
                out["price_grid"], out["grids"][metric][idx]
            )


def test_mid_snapshot_mode_reuses_incumbent_iv_solver_and_matches_horizon_zero():
    contracts = []
    for strike in (95.0, 100.0, 105.0):
        for right in ("C", "P"):
            T = 7.0 / 365.0
            iv = 0.25
            mid = float(
                bs_price(
                    SPOT,
                    np.asarray([strike], float),
                    np.asarray([T], float),
                    np.asarray([iv], float),
                    np.asarray([right == "C"], bool),
                )[0]
            )
            contracts.append({
                "strike": strike,
                "exp_years": T,
                "mid": mid,
                "oi": (2200.0 + strike) if right == "C" else (700.0 + strike),
                "right": right,
                "expiry": "2026-09-25",
            })

    out = _build(
        contracts,
        price_grid=[99, 100, 101],
        horizons_minutes=[0],
        iv_source="solve_from_mid",
        iv_observed_at="2026-09-18T13:59:59Z",
    )
    incumbent = compute_greek_grids(
        contracts,
        spot=SPOT,
        union_strikes=[95.0, 100.0, 105.0],
    )
    assert incumbent.n_contracts == len(contracts)
    assert out["source_counts"]["iv_solved"] == len(contracts)
    assert out["assumptions"]["iv_source"] == "solve_from_mid"
    assert out["grids"]["gex"][0][1] == pytest.approx(sum(incumbent.gex))
    assert out["grids"]["vex"][0][1] == pytest.approx(sum(incumbent.vex))
    assert out["grids"]["cex"][0][1] == pytest.approx(sum(incumbent.cex))


def test_source_clock_and_oi_vintage_cannot_come_from_after_market_observation():
    with pytest.raises(ValueError, match="iv_observed_at"):
        _build(iv_observed_at="2026-09-18T14:00:01Z")
    with pytest.raises(ValueError, match="oi_vintage"):
        _build(oi_vintage="2026-09-19")
    with pytest.raises(ValueError, match="oi_vintage"):
        _build(oi_vintage="not-a-date")


def test_live_flow_contract_shape_uses_exp_str_for_scope_and_preserves_source_clocks():
    T = 1.0 / 365.0
    contracts = []
    for strike, right, oi, trade_at, quote_at in [
        (99.0, "C", 1800.0, "2026-09-18T13:59:50Z", "2026-09-18T13:59:49.500000Z"),
        (100.0, "P", 1400.0, "2026-09-18T13:59:55Z", "2026-09-18T13:59:54.500000Z"),
    ]:
        mid = float(
            bs_price(
                SPOT,
                np.asarray([strike], float),
                np.asarray([T], float),
                np.asarray([0.24], float),
                np.asarray([right == "C"], bool),
            )[0]
        )
        contracts.append({
            # Canonical #7279 live-flow key is exp_str, not expiry.
            "exp_str": "2026-09-19",
            "exp_years": T,
            "strike": strike,
            "right": right,
            "mid": mid,
            "oi": oi,
            "trade_at": trade_at,
            "quote_at": quote_at,
        })

    out = _build(
        contracts,
        price_grid=[99, 100, 101],
        horizons_minutes=[0],
        expiry_scope=["2026-09-19"],
        iv_source="solve_from_mid",
        iv_observed_at="2026-09-18T13:59:56Z",
        oi_vintage="2026-09-17",
    )
    assert out["source_counts"]["valid_snapshot"] == 2
    assert out["source_counts"]["omitted_scope"] == 0
    assert out["expiry_scope"] == ["2026-09-19"]
    assert out["source_clocks"]["trade_at_first"] == "2026-09-18T13:59:50Z"
    assert out["source_clocks"]["trade_at_last"] == "2026-09-18T13:59:55Z"
    assert out["source_clocks"]["quote_at_first"] == "2026-09-18T13:59:49.500000Z"
    assert out["source_clocks"]["quote_at_last"] == "2026-09-18T13:59:54.500000Z"


def test_mixed_unknown_live_quote_clock_fails_scenario_envelope_closed():
    contracts = _contracts()[:2]
    contracts[0]["trade_at"] = "2026-09-18T13:59:50Z"
    contracts[0]["quote_at"] = "2026-09-18T13:59:49Z"
    contracts[1]["trade_at"] = "2026-09-18T13:59:55Z"
    contracts[1]["quote_at"] = None
    out = _build(contracts, horizons_minutes=[0])
    assert out["source_clocks"]["trade_at_first"] == "2026-09-18T13:59:50Z"
    assert out["source_clocks"]["trade_at_last"] == "2026-09-18T13:59:55Z"
    assert out["source_clocks"]["quote_at_first"] is None
    assert out["source_clocks"]["quote_at_last"] is None


def test_conflicting_expiry_aliases_and_future_contract_clocks_fail_closed():
    contract = _contracts()[0]
    contract["exp_str"] = "2026-09-20"
    out = _build([contract], horizons_minutes=[0])
    assert out["source_counts"]["valid_snapshot"] == 0
    assert out["source_counts"]["omitted_invalid"] == 1

    future = _contracts()[0]
    future["trade_at"] = "2026-09-18T14:00:01Z"
    future["quote_at"] = "2026-09-18T13:59:59Z"
    with pytest.raises(ValueError, match="trade_at"):
        _build([future], horizons_minutes=[0])


def test_scenario_rejects_same_day_oi_and_unknown_iv_clock_for_mid_solve():
    # Existing options timing law: OI must be from a strictly prior session/date,
    # never the same observation date.
    with pytest.raises(ValueError, match="oi_vintage"):
        _build(oi_vintage="2026-09-18")

    # When this engine itself solves IV from mids, the IV observation clock is part
    # of the frozen information set and cannot be omitted.
    with pytest.raises(ValueError, match="iv_observed_at"):
        _build(iv_source="solve_from_mid")


def test_invalid_or_unsupported_scenario_inputs_fail_closed():
    with pytest.raises(ValueError, match="timezone"):
        _build(observed_at="2026-09-18T14:00:00")
    with pytest.raises(ValueError, match="sticky_strike"):
        _build(vol_map="sticky_delta")
    with pytest.raises(ValueError, match="iv_source"):
        _build(iv_source="magic")
    with pytest.raises(ValueError, match="price_grid"):
        _build(price_grid=[100])
    with pytest.raises(ValueError, match="horizons"):
        _build(horizons_minutes=[-1])
    with pytest.raises(ValueError, match="timezone"):
        _build(iv_observed_at="2026-09-18T13:59:59")
    with pytest.raises(ValueError, match="mult/pm"):
        _build(pm=0.0)
    with pytest.raises(ValueError, match="mult/pm"):
        _build(mult=float("inf"))


def test_numerical_overflow_fails_cell_closed_instead_of_serializing_infinity():
    contracts = _contracts()
    for contract in contracts:
        contract["oi"] = 1e308
    out = _build(contracts, price_grid=[99, 100, 101], horizons_minutes=[0])
    assert out["grids"]["gex"][0] == [None, None, None]
    json.dumps(out, allow_nan=False)


def test_builder_does_not_mutate_snapshot_contracts():
    contracts = _contracts()
    before = copy.deepcopy(contracts)
    _build(contracts)
    assert contracts == before


def test_cli_is_a_machine_projection_without_a_new_store(tmp_path):
    payload = {
        "root": "SPY",
        "observed_at": OBS,
        "spot": SPOT,
        "price_grid": [95, 100, 105],
        "horizons_minutes": [0, 30],
        "oi_vintage": "2026-09-17",
        "iv_observed_at": "2026-09-18T13:59:58Z",
        "contracts": _contracts(),
    }
    src = tmp_path / "snapshot.json"
    src.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "scripts/build_options_scenario_surface.py", "--input", str(src), "--output", "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(proc.stdout)
    assert out["schema"] == SCHEMA
    assert out["product_kind"] == PRODUCT_KIND
    assert out["root"] == "SPY"
    assert out["horizons_minutes"] == [0, 30]
    assert out["source_clocks"]["oi_vintage"] == "2026-09-17"
    assert out["source_clocks"]["iv_observed_at"] == "2026-09-18T13:59:58Z"
    assert len(out["grids"]["gex"]) == 2


# ---------------------------------------------------------------------------
# Integrated order/unknown/future clock controls.
# Source: review 5399568840 test_scenario_clock_order_review.py
# (sha256 cd2eb6fa5424a6613a8291be13a5f919502ed84ec82f5eeb690180084da9e0c4).
# The review module's module-level helper/constant names (OBS, PAST, LATER_PAST,
# FUTURE, UNKNOWN, rows, build) are prefixed to avoid colliding with the
# incumbent globals (OBS, SPOT, _contracts, _build). Test functions are kept
# verbatim so the accepted 52 parameterized cases collect unchanged.
# ---------------------------------------------------------------------------
REV_OBS = "2026-09-18T14:00:00.123456Z"
REV_PAST = "2026-09-18T13:59:58Z"
REV_LATER_PAST = "2026-09-18T13:59:59Z"
REV_FUTURE = "2026-09-18T14:00:01Z"
REV_UNKNOWN = [None, "", "not-a-timestamp", "2026-09-18T13:59:57"]


def _review_rows(iv_source):
    result = []
    for strike, right in [(99.0, "C"), (100.0, "P")]:
        row = dict(strike=strike, right=right, exp_years=1 / 365, oi=1200,
                   exp_str="2026-09-19", trade_at=REV_PAST, quote_at=REV_PAST)
        if iv_source == "provided_iv":
            row["iv"] = 0.24
        else:
            row["mid"] = float(bs_price(100.0, np.array([strike]),
                np.array([1/365]), np.array([.24]), np.array([right == "C"]))[0])
        result.append(row)
    return result


def _review_build(contracts, iv_source):
    before = copy.deepcopy(contracts)
    try:
        return build_scenario_surface(contracts, root="SPY", observed_at=REV_OBS,
            spot=100., price_grid=[99., 100., 101.], horizons_minutes=[0, 60],
            iv_source=iv_source, iv_observed_at=REV_PAST, oi_vintage="2026-09-17")
    finally:
        assert contracts == before


@pytest.mark.parametrize("iv_source", ["provided_iv", "solve_from_mid"])
@pytest.mark.parametrize("field", ["trade_at", "quote_at"])
@pytest.mark.parametrize("unknown", REV_UNKNOWN)
@pytest.mark.parametrize("future_first", [False, True])
def test_future_clock_is_rejected_despite_an_unknown_member(iv_source, field, unknown, future_first):
    contracts = _review_rows(iv_source)
    contracts[0][field] = unknown
    contracts[1][field] = REV_FUTURE
    if future_first:
        contracts.reverse()
    with pytest.raises(ValueError, match=field):
        _review_build(contracts, iv_source)


@pytest.mark.parametrize("iv_source", ["provided_iv", "solve_from_mid"])
@pytest.mark.parametrize("field", ["trade_at", "quote_at"])
@pytest.mark.parametrize("unknown", REV_UNKNOWN)
def test_mixed_unknown_past_still_has_no_known_only_envelope(iv_source, field, unknown):
    contracts = _review_rows(iv_source)
    contracts[0][field] = unknown
    contracts[1][field] = REV_LATER_PAST
    for ordered in (contracts, list(reversed(contracts))):
        result = _review_build(ordered, iv_source)
        assert result["source_counts"]["valid_snapshot"] == 2
        assert result["source_clocks"][field + "_first"] is None
        assert result["source_clocks"][field + "_last"] is None
        assert result["grids"]["gex"][0][1] is not None


@pytest.mark.parametrize("iv_source", ["provided_iv", "solve_from_mid"])
@pytest.mark.parametrize("field", ["trade_at", "quote_at"])
def test_all_known_past_bounds_remain_exact(iv_source, field):
    contracts = _review_rows(iv_source)
    contracts[1][field] = REV_LATER_PAST
    for ordered in (contracts, list(reversed(contracts))):
        result = _review_build(ordered, iv_source)
        assert result["source_clocks"][field + "_first"] == REV_PAST
        assert result["source_clocks"][field + "_last"] == REV_LATER_PAST
