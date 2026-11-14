"""Fault injection for the independent arithmetic readback, not performance evidence."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from scripts import prophet_fusion_mechanism_verify as v
from scripts.prophet_fusion_mechanisms import MechanismRefusal


@pytest.fixture
def case():
    index = pd.bdate_range("2018-01-01", periods=500)
    rng = np.random.default_rng(2026)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(.0004, .012, len(index)))), index=index)
    benchmark = pd.Series(100 * np.exp(np.cumsum(rng.normal(.0001, .009, len(index)))), index=index)
    spec = {"universe": ["AAPL"], "start": "2018-01-01", "end": "2019-12-31",
            "triggers": ["technical_core_t12"], "cost_sensitivity_bps": [0, 10, 25, 50],
            "primary_round_trip_cost_bps": 25}
    i = 310
    ma = benchmark.rolling(200).mean()
    returns = benchmark / benchmark.shift(1) - 1
    rows = []
    for horizon in (21, 63):
        a, b = float(close.iloc[i + 1]), float(close.iloc[i + horizon + 1])
        window = close.iloc[i + 2:i + horizon + 2] / a - 1
        row = {"ticker": "AAPL", "date": index[i], "trigger": "technical_core_t12",
               "horizon": horizon, "fill_date": str(index[i + 1].date()),
               "exit_date": str(index[i + horizon + 1].date()), "gross_return": b / a - 1,
               "benchmark_return": float(benchmark.iloc[i + horizon + 1] / benchmark.iloc[i + 1] - 1),
               "forward_mdd_close": min(0., float(window.min())),
               "forward_mfe_close": max(0., float(window.max())),
               "market_uptrend": bool(benchmark.iloc[i] > ma.iloc[i] and ma.iloc[i] > ma.iloc[i - 20]),
               "no_volatility_stress": bool(returns.rolling(21).std().iloc[i] <= 1.5 * returns.rolling(252).std().iloc[i])}
        for cost in spec["cost_sensitivity_bps"]:
            row[f"net_{cost}bps"] = (b / a) * (1 - cost / 20000) / (1 + cost / 20000) - 1
        row["net_return"] = row["net_25bps"]
        row["net_excess"] = row["net_return"] - row["benchmark_return"]
        row["net_positive"] = float(row["net_return"] > 0)
        rows.append(row)
    return pd.DataFrame(rows), {"AAPL": close}, benchmark, spec


def test_every_row_recomputed_without_original_grader(case):
    result = v.verify_rows(*case)
    assert result["events_verified"] == 2
    assert result["all_price_fill_cost_and_context_checks"]
    assert result["maximum_net_return_absolute_error"] < 1e-12


@pytest.mark.parametrize("column", ["gross_return", "benchmark_return", "net_return", "net_excess",
                                     "net_0bps", "net_25bps", "forward_mdd_close", "forward_mfe_close"])
def test_small_favorable_tampering_is_rejected(case, column):
    events, prices, market, spec = case
    events.loc[0, column] += .0001
    with pytest.raises(MechanismRefusal, match="MISMATCH"):
        v.verify_rows(events, prices, market, spec)


def test_wrong_clock_refused(case):
    events, prices, market, spec = case
    events.loc[0, "fill_date"] = str(events.loc[0, "date"].date())
    with pytest.raises(MechanismRefusal, match="FILL_DATE"):
        v.verify_rows(events, prices, market, spec)


def test_null_context_does_not_turn_into_true(case):
    events, prices, market, spec = case
    events["market_uptrend"] = events["market_uptrend"].astype(object)
    events.loc[0, "market_uptrend"] = np.nan
    with pytest.raises(MechanismRefusal, match="BOOLEAN"):
        v.verify_rows(events, prices, market, spec)


def test_duplicate_trade_cannot_inflate_result(case):
    events, prices, market, spec = case
    with pytest.raises(MechanismRefusal, match="DUPLICATE"):
        v.verify_rows(pd.concat([events, events.iloc[:1]], ignore_index=True), prices, market, spec)


def test_other_asset_is_not_silently_accepted(case):
    events, prices, market, spec = case
    events.loc[0, "ticker"] = "MSFT"
    with pytest.raises(MechanismRefusal, match="UNIVERSE"):
        v.verify_rows(events, prices, market, spec)


def test_source_drift_fails_before_claiming_pinned_native_engine(monkeypatch):
    monkeypatch.setattr(v.subprocess, "run", lambda *args, **kw: SimpleNamespace(stdout="engine/grading.py\n"))
    with pytest.raises(MechanismRefusal, match="NATIVE_SOURCE_DRIFT"):
        v.assert_native_source("a" * 40)


def test_dirty_native_module_cannot_be_hidden_as_new_file(monkeypatch):
    calls = iter([SimpleNamespace(stdout=""), SimpleNamespace(stdout="engine/untracked.py\n")])
    monkeypatch.setattr(v.subprocess, "run", lambda *args, **kw: next(calls))
    with pytest.raises(MechanismRefusal, match="UNTRACKED_NATIVE"):
        v.assert_native_source("a" * 40)


def test_source_is_actual_immutable_commit(monkeypatch):
    with pytest.raises(MechanismRefusal, match="PIN_REQUIRED"):
        v.assert_native_source("main")


def test_missing_value_must_stay_missing():
    with pytest.raises(MechanismRefusal, match="EXPECTED_UNKNOWN"):
        v.number_equal(.0, None, "unknown")
    v.number_equal(None, None, "unknown")
