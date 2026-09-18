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

from engine.intraday_greeks import bs_greeks_vec
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
    assert out["horizon_meta"][2]["contract_coverage"] == 0.0
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


def test_invalid_or_unsupported_scenario_inputs_fail_closed():
    with pytest.raises(ValueError, match="timezone"):
        _build(observed_at="2026-09-18T14:00:00")
    with pytest.raises(ValueError, match="sticky_strike"):
        _build(vol_map="sticky_delta")
    with pytest.raises(ValueError, match="price_grid"):
        _build(price_grid=[100])
    with pytest.raises(ValueError, match="horizons"):
        _build(horizons_minutes=[-1])


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
    assert len(out["grids"]["gex"]) == 2
