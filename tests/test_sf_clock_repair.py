"""Regression tests for the Chairman-approved target-price-clock repair.

All price and feature fixtures are synthetic. Every writer is confined to tmp_path.
The old row-stride selector and native-frequency annualization must fail these tests.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine.signal_foundry import harness
from engine.validation import backtest_core


def _selector():
    fn = getattr(harness, "_nonoverlap_price_windows", None)
    assert callable(fn), "Missing target-price-clock window selector"
    return fn


def _spec(feature_path="feature.csv", horizon=63):
    return {
        "id": "SF-9801", "name": "Synthetic clock regression", "market": "US test",
        "thesis": "A fixture, never market evidence",
        "data": [{"path": feature_path, "column": "feature", "pit": "synthetic"}],
        "feature": {"pipeline": [["lag", {"n": 0}]]},
        "target": {"path": "price.csv", "column": "price",
                   "kind": "absolute_return", "horizon_d": horizon},
        "universe": "single_series", "baseline": "buy_and_hold",
        "gates": {"min_t_hac": 2.0, "fdr_q": 0.1, "dsr": 0.9},
        "registered_at": "2026-09-15",
    }


def _prices(tmp_path, n=2521, freq="B"):
    dates = pd.date_range("2000-01-03", periods=n, freq=freq)
    returns = 0.0002 + 0.003 * np.sin(np.arange(n) / 13.0)
    prices = pd.Series(100 * np.cumprod(1 + returns), index=dates, name="price")
    prices.to_frame().to_csv(tmp_path / "price.csv")
    return prices


def test_daily_selector_preserves_known_nonoverlap_windows():
    price_dates = pd.bdate_range("2000-01-03", periods=600)
    observed = price_dates[:500]
    actual = _selector()(observed, price_dates, 63)
    np.testing.assert_array_equal(actual, np.arange(0, 500, 63))


def test_monthly_observations_do_not_turn_63_bars_into_63_months():
    price_dates = pd.bdate_range("2000-01-03", periods=6000)
    observed = price_dates[np.arange(0, 5250, 21)]
    actual = _selector()(observed, price_dates, 63)
    np.testing.assert_array_equal(actual, np.arange(0, 250, 3))
    assert len(actual) == 84
    assert len(observed[::63]) == 4  # the original defect


def test_irregular_observations_use_actual_target_positions():
    price_dates = pd.bdate_range("2000-01-03", periods=400)
    positions = np.array([0, 1, 10, 62, 63, 64, 125, 126, 200, 264])
    actual = _selector()(price_dates[positions], price_dates, 63)
    np.testing.assert_array_equal(actual, [0, 4, 7, 8, 9])
    assert np.all(np.diff(positions[actual]) >= 63)


@pytest.mark.parametrize("fault", ["duplicate", "unsorted", "missing", "immature"])
def test_invalid_window_clocks_fail_closed(fault):
    price_dates = pd.bdate_range("2000-01-03", periods=100)
    observed = price_dates[:20]
    if fault == "duplicate":
        observed = observed.insert(1, observed[0])
    elif fault == "unsorted":
        observed = observed[::-1]
    elif fault == "missing":
        observed = pd.DatetimeIndex(["2000-01-08"])
    else:
        observed = price_dates[-1:]
    with pytest.raises(ValueError):
        _selector()(observed, price_dates, 21)


@pytest.mark.parametrize("horizon", [0, -1, True, 1.5])
def test_invalid_horizon_fails_closed(horizon):
    dates = pd.bdate_range("2000-01-03", periods=100)
    with pytest.raises(ValueError):
        _selector()(dates[:20], dates, horizon)


def test_monthly_backtest_keeps_target_price_bars(tmp_path):
    prices = _prices(tmp_path)
    feature = pd.Series(1.0, index=prices.index[::21])
    actual = harness._run_backtest_raw(_spec(), feature, tmp_path)
    assert actual is not None
    assert actual["net"].index.equals(prices.index)
    expected = backtest_core(prices, pd.Series(1.0, index=prices.index), cost_bps=8.0)
    # CSV stores timestamps, not pandas frequency metadata; values and dates remain asserted.
    pd.testing.assert_series_equal(actual["net"], expected["net"], check_freq=False)


def test_monthly_backtest_cagr_uses_elapsed_years(tmp_path):
    prices = _prices(tmp_path)
    feature = pd.Series(1.0, index=prices.index[::21])
    summary = harness._run_backtest(_spec(), feature, tmp_path)
    expected = backtest_core(prices, pd.Series(1.0, index=prices.index), cost_bps=8.0)
    years = (prices.index[-1] - prices.index[0]).total_seconds() / (365.25 * 86400)
    expected_cagr = float((1 + expected["net"].iloc[1:]).prod() ** (1 / years) - 1)
    assert summary["cagr_net"] == pytest.approx(round(expected_cagr, 4), abs=1e-4)
    assert summary.get("clock") == "target_price_bars"
    assert summary.get("return_bars") == len(prices) - 1


def test_seven_day_target_annualization_is_not_252(tmp_path):
    prices = _prices(tmp_path, n=2556, freq="D")
    feature = pd.Series(1.0, index=prices.index)
    summary = harness._run_backtest(_spec(), feature, tmp_path)
    assert summary.get("periods_per_year") == pytest.approx(365.25, abs=0.01)


def test_backtest_never_backfills_before_first_feature_or_extends_after_last(tmp_path):
    prices = _prices(tmp_path)
    feature = pd.Series(1.0, index=prices.index[21:-21:21])
    actual = harness._run_backtest_raw(_spec(), feature, tmp_path)
    assert actual is not None
    assert actual["net"].index[0] == feature.index[0]
    assert actual["net"].index[-1] == feature.index[-1]
    assert len(actual["net"]) > len(feature)


def test_circular_placebo_has_no_legal_shift_when_both_edges_overlap():
    feature = np.sin(np.arange(30))
    result = harness._time_shift_placebo_ic(feature, feature, n_draws=20, min_shift=21)
    assert result == {}, "A near-full rotation is a forbidden short reverse lag"


def test_monthly_run_uses_nonoverlapping_price_windows(tmp_path):
    prices = _prices(tmp_path, n=6301)
    dates = prices.index[::21]
    pd.Series(np.sin(np.arange(len(dates)) / 7.0), index=dates,
              name="feature").to_frame().to_csv(tmp_path / "feature.csv")
    result = harness.run_spec(_spec(), repo_root=tmp_path,
                              ledger_path=tmp_path / "trial_ledger.jsonl")
    stats = result["stats"]
    assert stats["hac"]["n"] >= 80, stats["hac"]
    sampling = stats.get("sampling", {})
    assert sampling.get("clock") == "target_price_bars"
    assert sampling.get("horizon_bars") == 63
    assert sampling.get("n_nonoverlap") == stats["hac"]["n"]
    assert result["battery_version"] != "sf-battery-1"


@pytest.mark.parametrize("spacing,expected", [(1, 63), (5, 13), (21, 3)])
def test_placebo_row_radius_maps_from_actual_price_clock(spacing, expected):
    fn = getattr(harness, "_price_horizon_row_radius", None)
    assert callable(fn), "Missing price-clock to observation-row dependence mapping"
    dates = pd.bdate_range("2000-01-03", periods=6000)
    observed = dates[np.arange(0, 5250, spacing)]
    assert fn(observed, dates, 63) == expected


def test_negative_lag_uses_three_months_not_sixty_three_months():
    fn = getattr(harness, "_negative_lag_price_clock_ic", None)
    assert callable(fn), "Missing timestamp-aware negative-lag placebo"
    dates = pd.bdate_range("2000-01-03", periods=6000)
    observed = dates[np.arange(0, 5250, 21)]
    rng = np.random.default_rng(781)
    f = pd.Series(rng.standard_normal(len(observed)), index=observed)
    y = pd.Series(rng.standard_normal(len(observed)), index=observed)
    result = fn(f, y, dates, 63)
    expected = harness._negative_lag_placebo_ic(f.to_numpy(), y.to_numpy(), 3)
    assert result["n_pairs"] == 247
    assert result["neg_lag_ic"] == expected["neg_lag_ic"]
    assert result["obs_ic_same_window"] == expected["obs_ic_same_window"]


def _passing_evidence():
    return dict(spec_id="SF-9801", full_ic=0.3, hac_stat={"t": 4.0},
                block_ci={"ci_2p5": 0.1, "ci_97p5": 0.4, "ci_straddles_0": False},
                shift_plac={"shift_pctile": 0.99},
                neg_plac={"neg_lag_ic": 0.1, "obs_ic_same_window": 0.3,
                          "neg_dominates": False},
                era={}, split_half={"split_half_sign_flip": False},
                dsr_result={"dsr": 0.95}, t_hac_gate=2.0, dsr_gate=0.9, n_obs=100)


@pytest.mark.parametrize("fault", ["missing_bootstrap", "missing_shift", "missing_negative",
                                    "nan_t", "nan_dsr", "nan_ic", "inf_t"])
def test_unavailable_or_nonfinite_evidence_never_passes(fault):
    args = _passing_evidence()
    if fault.startswith("missing_"):
        key = {"missing_bootstrap": "block_ci", "missing_shift": "shift_plac",
               "missing_negative": "neg_plac"}[fault]
        args[key] = {}
    elif fault == "nan_t":
        args["hac_stat"] = {"t": float("nan")}
    elif fault == "inf_t":
        args["hac_stat"] = {"t": float("inf")}
    elif fault == "nan_dsr":
        args["dsr_result"] = {"dsr": float("nan")}
    else:
        args["full_ic"] = float("nan")
    verdict, _ = harness._compute_verdict(**args)
    assert verdict != "pass_candidate"


def test_power_floor_uses_nonoverlap_count_without_calling_it_independence():
    import inspect
    assert "n_nonoverlap" in inspect.signature(harness._compute_verdict).parameters
    args = _passing_evidence()
    args.update(n_obs=1000, n_nonoverlap=24)
    verdict, reasons = harness._compute_verdict(**args)
    assert verdict == "insufficient_power"
    assert "24" in " ".join(reasons)


def test_clock_regressions_are_enrolled_with_the_existing_foundry_ci():
    from pathlib import Path
    import yaml
    root = Path(__file__).resolve().parents[1]
    manifest = yaml.safe_load((root / ".github/ci/legacy-jobs.yml").read_text())
    steps = manifest["jobs"]["causal-factory"]["steps"]
    command = "\n".join(str(step.get("run", "")) for step in steps)
    assert "tests/test_sf_clock_repair.py" in command
    assert "tests/test_sf_harness.py" in command


@pytest.mark.parametrize("field,value", [("t", 1.99), ("dsr", 0.8999)])
def test_declared_admission_thresholds_are_not_lowered(field, value):
    args = _passing_evidence()
    if field == "t":
        args["hac_stat"]["t"] = value
    else:
        args["dsr_result"]["dsr"] = value
    verdict, _ = harness._compute_verdict(**args)
    assert verdict == "null"


def test_required_price_clock_backtest_failure_is_explicit(tmp_path, monkeypatch):
    prices = _prices(tmp_path)
    feature = pd.Series(1.0, index=prices.index[::21])
    monkeypatch.setattr(harness, "_run_backtest_raw", lambda *args, **kwargs: None)
    result = harness._run_backtest(_spec(), feature, tmp_path)
    assert result.get("error"), "A required return stream cannot disappear into an empty dict"


def test_return_candidate_cannot_pass_after_cost_aware_backtest_failure(tmp_path, monkeypatch):
    prices = _prices(tmp_path, n=2521)
    pd.Series(np.sin(np.arange(len(prices)) / 17.0), index=prices.index,
              name="feature").to_frame().to_csv(tmp_path / "feature.csv")
    monkeypatch.setattr(harness, "_run_backtest", lambda *args, **kwargs: {"error": "fixture"})
    verdict_calls = []

    def would_pass(*args, **kwargs):
        verdict_calls.append(True)
        return "pass_candidate", ["test fixture: other numerical evidence would pass"]

    monkeypatch.setattr(harness, "_compute_verdict", would_pass)
    result = harness.run_spec(_spec(), repo_root=tmp_path,
                              ledger_path=tmp_path / "trial_ledger.jsonl")
    assert result["verdict"] == "error"
    assert not verdict_calls, "Do not adjudicate a supported-return candidate without its return stream"
    assert "backtest" in " ".join(result["verdict_reasons"]).lower()


@pytest.mark.parametrize("output", ["data", ".pytest_cache", ".pytest_cache/existing"])
def test_reproduction_artifact_refuses_nonprivate_or_existing_output(tmp_path, monkeypatch, output):
    import importlib.util
    from pathlib import Path
    import sys
    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/signal-lab-clock-repair-20260915/recheck.py"
    spec = importlib.util.spec_from_file_location("sf_clock_recheck_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path
    (tmp_path / ".pytest_cache/existing").mkdir(parents=True)
    sentinel = tmp_path / ".pytest_cache/existing/keep.txt"
    sentinel.write_text("untouched")
    monkeypatch.setattr(sys, "argv", [str(path), "--output", output])
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2
    assert sentinel.read_text() == "untouched"
    assert not (tmp_path / "data").exists()


def test_summary_and_dsr_use_one_identical_return_stream(tmp_path, monkeypatch):
    """A second evaluation can read changed data or fail and silently use a proxy."""
    prices = _prices(tmp_path, n=2521)
    pd.Series(np.sin(np.arange(len(prices)) / 17.0), index=prices.index,
              name="feature").to_frame().to_csv(tmp_path / "feature.csv")
    original = harness._run_backtest_raw
    calls = []

    def once_only(*args, **kwargs):
        calls.append(True)
        if len(calls) > 1:
            raise RuntimeError("the input snapshot must not be reevaluated")
        return original(*args, **kwargs)

    monkeypatch.setattr(harness, "_run_backtest_raw", once_only)
    result = harness.run_spec(_spec(), repo_root=tmp_path,
                              ledger_path=tmp_path / "trial_ledger.jsonl")
    assert len(calls) == 1, "Reported returns and DSR must share one computed stream"
    dsr = result.get("stats", {}).get("dsr")
    if dsr is not None:
        assert dsr["dsr_series"] == "strategy_net_return"
