"""Conditional price x future-time options surface — R2 scenario-field contract."""
from __future__ import annotations

import copy
import importlib
import importlib.util
import json
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
