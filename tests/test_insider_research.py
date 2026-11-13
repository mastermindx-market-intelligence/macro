"""Native Insider filing-window and rebalance arithmetic contracts.

Synthetic prices diagnose source behavior; they do not requalify a research tier.
The state oracle constructs fresh targets and carries an explicit daily portfolio,
independently of the harnesses' forward-filled weight matrices.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_series_equal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.insider_factor import build_signals  # noqa: E402
from scripts import insider_phase0 as phase0, insider_phase1 as phase1  # noqa: E402


def _filings(rows):
    p = pd.DataFrame(rows, columns=[
        "ticker", "code", "filing_date", "rptownercik", "usd", "is_routine"])
    p["filing_date"] = pd.to_datetime(p["filing_date"])
    p["is_officer"] = True
    p["is_director"] = False
    p["is_tenpct"] = False
    p["title"] = ""
    return p


@pytest.mark.parametrize("months", [1, 2, 3, 6])
def test_buyer_breadth_deduplicates_across_the_complete_filing_window(months):
    p = _filings([("A", "P", f"2025-{m:02}-10", "repeat", 100.0, False)
                  for m in range(7-months, 7)])
    d = pd.Timestamp("2025-06-30")
    s = build_signals(p, [d], k_months=6)
    assert s["n_buyers"].loc[d, "A"] == 1
    assert s["opp_buyers"].loc[d, "A"] == 1
    assert s["buy_usd"].loc[d, "A"] == 100.0 * months


def test_distinct_owners_are_per_ticker_and_opportunistic_filter_precedes_dedup():
    p = _filings([
        ("A", "P", "2025-05-10", "I", 100.0, False),
        ("A", "P", "2025-06-10", "I", 200.0, True),
        ("A", "P", "2025-06-11", "I", 300.0, False),
        ("A", "P", "2025-06-12", "J", 400.0, True),
        ("B", "P", "2025-06-12", "I", 500.0, False),
        ("ROUTINE", "P", "2025-06-13", "R", 600.0, True),
    ])
    d = pd.Timestamp("2025-06-30")
    s = build_signals(p, [d])
    assert s["n_buyers"].loc[d, "A"] == 2
    assert s["opp_buyers"].loc[d, "A"] == 1
    assert s["opp_buy_usd"].loc[d, "A"] == 400.0
    assert s["opp_buyers"].loc[d, "B"] == 1
    assert "ROUTINE" not in s["opp_buy_usd"].columns
    assert "ROUTINE" not in s["opp_buyers"].columns


@pytest.mark.parametrize("name,expected", [
    ("buy_usd", 10.0), ("net_usd", 6.0), ("n_buyers", 1.0),
    ("opp_buy_usd", 10.0), ("opp_buyers", 1.0), ("role_buy_usd", 10.0),
])
def test_every_signal_respects_the_actual_same_month_filing_cutoff(name, expected):
    p = _filings([
        ("A", "P", "2025-01-10", "I", 10.0, False),
        ("A", "S", "2025-01-20", "S", 4.0, False),
        ("A", "P", "2025-01-31", "FUTURE", 1000.0, False),
        ("A", "S", "2025-01-31", "FUTURE_SELL", 300.0, False),
    ])
    p.loc[p.rptownercik == "FUTURE", "title"] = "Chief Executive Officer"
    early, late = pd.Timestamp("2025-01-30"), pd.Timestamp("2025-01-31")
    s = build_signals(p, [late, early])
    assert list(s[name].index) == [late, early]
    assert s[name].loc[early, "A"] == expected
    assert s["net_usd"].loc[late, "A"] == 706.0
    assert s["role_buy_usd"].loc[late, "A"] == 1510.0


def test_window_start_is_inclusive_and_old_owners_and_sales_expire():
    p = _filings([
        ("A", "P", "2024-12-31", "OLD", 1000.0, False),
        ("A", "S", "2024-12-31", "OLD_SELL", 800.0, False),
        ("A", "P", "2025-01-01", "BOUNDARY", 11.0, False),
        ("A", "P", "2025-06-30", "CURRENT", 13.0, False),
        ("A", "S", "2025-06-30", "SELL", 3.0, False),
    ])
    d = pd.Timestamp("2025-06-30")
    s = build_signals(p, [d], k_months=6)
    assert s["buy_usd"].loc[d, "A"] == 24.0
    assert s["net_usd"].loc[d, "A"] == 21.0
    assert s["n_buyers"].loc[d, "A"] == 2
    one = build_signals(p, [d], k_months=1)
    assert one["n_buyers"].loc[d, "A"] == 1
    assert one["net_usd"].loc[d, "A"] == 10.0


def test_signal_support_and_observed_month_coverage_are_preserved():
    p = _filings([
        ("BUY", "P", "2025-01-10", "I", 10.0, False),
        ("ROUTINE", "P", "2025-01-15", "R", 20.0, True),
        ("SELL_ONLY", "S", "2025-03-10", "S", 7.0, False),
    ])
    before, first, gap, last, after = pd.to_datetime([
        "2024-12-31", "2025-01-31", "2025-02-28", "2025-03-31", "2025-04-30"])
    grid = [after, last, gap, first, before]
    mc = pd.DataFrame(100.0, index=grid, columns=["BUY", "SELL_ONLY", "UNSUPPORTED"])
    mc.loc[last, "SELL_ONLY"] = 0.0
    s = build_signals(p, grid, mcap=mc, k_months=1)
    assert list(s["buy_usd"].index) == [last, gap, first]
    assert list(s["buy_usd"].columns) == ["BUY", "ROUTINE"]
    assert s["buy_usd"].columns.name == "ticker"
    assert list(s["opp_buy_usd"].columns) == ["BUY"]
    assert list(s["net_usd"].columns) == ["BUY", "ROUTINE", "SELL_ONLY"]
    assert s["buy_usd"].loc[gap, "BUY"] == 0.0
    assert s["net_usd"].loc[last, "SELL_ONLY"] == -7.0
    assert pd.isna(s["net_usd_mcap"].loc[before, "BUY"])
    assert pd.isna(s["net_usd_mcap"].loc[after, "BUY"])
    assert pd.isna(s["net_usd_mcap"].loc[last, "SELL_ONLY"])
    assert "UNSUPPORTED" not in s["net_usd_mcap"].columns


def test_no_requested_date_in_observed_span_retains_empty_raw_matrices():
    p = _filings([("A", "P", "2025-01-10", "I", 10.0, False)])
    outside = pd.Timestamp("2025-02-28")
    for mat in build_signals(p, [outside]).values():
        assert mat.empty and len(mat.index) == 0 and len(mat.columns) == 0


def test_sell_only_panel_and_duplicate_requested_dates_keep_native_shape():
    p = _filings([("SELL", "S", "2025-01-10", "S", 7.0, False)])
    d = pd.Timestamp("2025-01-31")
    s = build_signals(p, [d, d])
    assert list(s["net_usd"].index) == [d]
    assert s["net_usd"].loc[d, "SELL"] == -7.0
    assert len(s["buy_usd"].columns) == 0


@pytest.mark.parametrize("bad", [0, -1, True, False, 1.0, 1.5, "1"])
def test_invalid_filing_window_is_not_silently_coerced(bad):
    p = _filings([("A", "P", "2025-01-10", "I", 10.0, False)])
    with pytest.raises(ValueError):
        build_signals(p, [pd.Timestamp("2025-01-31")], k_months=bad)


def test_numpy_integral_filing_window_remains_supported():
    p = _filings([("A", "P", "2025-01-10", "I", 10.0, False)])
    s = build_signals(p, [pd.Timestamp("2025-01-31")], k_months=np.int64(1))
    assert s["buy_usd"].iloc[0, 0] == 10.0


def _capture_native_statistics(monkeypatch, module):
    """Record exact inputs while executing every real statistical callback."""
    calls = {}
    for name in ("ret_moments", "deflated_sharpe", "block_bootstrap_ci"):
        original = getattr(module, name)

        def record(*args, _name=name, _original=original, **kwargs):
            call = {
                "args": tuple(a.copy() if hasattr(a, "copy") else a for a in args),
                "kwargs": kwargs.copy(),
            }
            calls.setdefault(_name, []).append(call)
            call["result"] = _original(*args, **kwargs)
            return call["result"]

        monkeypatch.setattr(module, name, record)
    return calls


def _target(names, longs=(), shorts=()):
    target = pd.Series(0.0, index=names)
    if len(longs):
        target.loc[list(longs)] = 1.0 / len(longs)
    if len(shorts):
        target.loc[list(shorts)] = -1.0 / len(shorts)
    return target


def _daily_state_oracle(R, targets, cost):
    """No weight matrix or forward fill: prior state earns today's return."""
    state = pd.Series(0.0, index=R.columns)
    values = []
    for d, row in R.iterrows():
        gross = float((state * row.clip(-0.5, 0.5)).sum())
        target = targets.get(d, state)
        turnover = float((target - state).abs().sum())
        values.append(gross - cost / 1e4 * turnover)
        state = target.copy()
    return pd.Series(values, index=R.index)


def _path_fixture(kind, *, long_only, cash_prefix, motion):
    dates = pd.to_datetime(["2025-01-31", "2025-02-03", "2025-02-28",
                            "2025-03-03", "2025-03-31", "2025-04-01"])
    grid = list(dates[[0, 2, 4]])
    index = dates.insert(0, pd.Timestamp("2025-01-30")) if cash_prefix else dates
    size = 50 if long_only else 25
    names = [f"N{i:03d}" for i in range(size * 2)]
    first, second = names[:size], names[size:]
    sig = pd.DataFrame(np.nan, index=grid, columns=names)
    sig.loc[grid[0], first] = np.arange(1, size + 1)
    sig.loc[grid[1], first] = np.arange(1, size + 1)
    membership = pd.DataFrame({
        "ticker": names, "start_date": pd.Timestamp("2020-01-01"), "end_date": pd.NaT})
    top_n = size // 5
    initial = _target(names, first[-top_n:], () if long_only else first[:top_n])
    initial_bench = _target(names, first) if long_only else None
    following, following_bench = initial.copy(), initial_bench
    if kind == "disjoint":
        sig.loc[grid[1]] = np.nan
        sig.loc[grid[1], second] = np.arange(1, size + 1)
        following = _target(names, second[-top_n:], () if long_only else second[:top_n])
        following_bench = _target(names, second) if long_only else None
    elif kind == "rotation":
        shift = 25 if long_only else 12
        sig.loc[grid[1], first] = np.roll(np.arange(1, size + 1), shift)
        following = (_target(names, first[15:25]) if long_only
                     else _target(names, first[7:12], first[12:17]))
    elif kind == "insufficient":
        sig.loc[grid[1], first[-1]] = np.nan
        following = _target(names)
        following_bench = _target(names) if long_only else None
    elif kind == "missing":
        sig = sig.drop(index=grid[1])
        following = _target(names)
        following_bench = _target(names) if long_only else None
    elif kind == "membership_exit":
        membership.loc[membership.ticker.isin(first), "end_date"] = grid[0]
        following = _target(names)
        following_bench = _target(names) if long_only else None
    elif kind == "ties":
        sig.loc[grid[1], first] = 1.0
        following = _target(names, first) if long_only else _target(names)
    elif kind == "zeros":
        sig.loc[grid[1], first] = 0.0
        following = _target(names)
    if grid[1] in sig.index:
        sig.loc[grid[2]] = sig.loc[grid[1]]
    else:
        sig = sig.drop(index=grid[2])
    R = pd.DataFrame(0.0, index=index, columns=names)
    if motion == "departed":
        R.loc[dates[3], first[-top_n:]] = 0.1
    elif motion == "benchmark":
        R.loc[dates[3], first[:-top_n]] = 0.1
    elif motion == "timing":
        R.loc[dates[2], first[-top_n:]] = 0.8
        if not long_only:
            R.loc[dates[2], first[:top_n]] = -0.8
        R.loc[dates[3], second[-top_n:]] = 0.12
    # Preserve the harnesses' distinct last-grid reporting behavior.
    R.loc[dates[-1], :] = np.linspace(-0.03, 0.04, len(names))
    targets = {grid[0]: initial, grid[1]: following, grid[2]: following}
    benchmarks = ({grid[0]: initial_bench, grid[1]: following_bench,
                   grid[2]: following_bench} if long_only else None)
    return R, sig, grid, membership, targets, benchmarks


@pytest.mark.parametrize("kind", [
    "unchanged", "disjoint", "rotation", "insufficient", "missing", "membership_exit", "ties"])
@pytest.mark.parametrize("cash_prefix", [False, True])
@pytest.mark.parametrize("motion", ["zero", "departed"])
def test_phase0_rebalance_path_matches_fresh_targets(monkeypatch, kind, cash_prefix, motion):
    R, sig, grid, members, targets, _ = _path_fixture(
        kind, long_only=False, cash_prefix=cash_prefix, motion=motion)
    expected = _daily_state_oracle(R, targets, 5.0).loc[grid[0]:grid[-1]]
    calls = _capture_native_statistics(monkeypatch, phase0)
    out = phase0.quintile_ls(R, sig, grid, n_trials=12, membership=members)
    actual = calls["block_bootstrap_ci"][0]["args"][0]
    assert_series_equal(actual, expected, check_names=False, atol=1e-12, rtol=1e-12)
    assert expected.iloc[0] == pytest.approx(-0.001)
    assert out["cum_pct"] == round(float(((1 + expected).prod() - 1) * 100), 1)
    assert out["n_days"] == len(expected)


@pytest.mark.parametrize("kind", [
    "unchanged", "disjoint", "rotation", "insufficient", "missing",
    "membership_exit", "ties", "zeros"])
@pytest.mark.parametrize("cash_prefix", [False, True])
@pytest.mark.parametrize("motion", ["departed", "benchmark"])
def test_phase1_portfolio_and_benchmark_clear_departed_targets(
        monkeypatch, kind, cash_prefix, motion):
    R, sig, grid, members, targets, benchmarks = _path_fixture(
        kind, long_only=True, cash_prefix=cash_prefix, motion=motion)
    port = _daily_state_oracle(R, targets, 5.0).loc[grid[0]:]
    bench = _daily_state_oracle(R, benchmarks, 0.0).loc[grid[0]:]
    expected = (port - bench).loc[:grid[-1]]
    calls = _capture_native_statistics(monkeypatch, phase1)
    out = phase1.long_only_tilt(R, sig, grid, members, top=0.2, n_trials=12)
    actual = calls["block_bootstrap_ci"][0]["args"][0]
    assert_series_equal(actual, expected, check_names=False, atol=1e-12, rtol=1e-12)
    assert expected.iloc[0] == pytest.approx(-0.0005)
    assert out["active_cum_pct"] == round(float(((1 + expected).prod() - 1) * 100), 1)
    assert out["port_sharpe"] == round(float(port.mean() / port.std() * np.sqrt(252)), 2)
    bench_sharpe = (round(float(bench.mean() / bench.std() * np.sqrt(252)), 2)
                    if bench.std() else None)
    assert out["bench_sharpe"] == bench_sharpe


@pytest.mark.parametrize("long_only", [False, True])
def test_rebalance_day_earns_old_holdings_and_preserves_clipped_returns(monkeypatch, long_only):
    R, sig, grid, members, targets, benchmarks = _path_fixture(
        "disjoint", long_only=long_only, cash_prefix=True, motion="timing")
    expected = _daily_state_oracle(R, targets, 5.0)
    module = phase1 if long_only else phase0
    calls = _capture_native_statistics(monkeypatch, module)
    if long_only:
        expected -= _daily_state_oracle(R, benchmarks, 0.0)
        module.long_only_tilt(R, sig, grid, members, top=0.2, n_trials=12)
    else:
        module.quintile_ls(R, sig, grid, n_trials=12, membership=members)
    assert_series_equal(calls["block_bootstrap_ci"][0]["args"][0],
                        expected.loc[grid[0]:grid[-1]], check_names=False,
                        atol=1e-12, rtol=1e-12)


@pytest.mark.parametrize("long_only", [False, True])
def test_long_native_path_preserves_bootstrap_and_dsr_callbacks(monkeypatch, long_only):
    size = 50 if long_only else 25
    names = [f"N{i:03d}" for i in range(size)]
    index = pd.bdate_range("2025-01-02", periods=130)
    grid = [index[0], index[45], index[90], index[125]]
    sig = pd.DataFrame([np.arange(1, size+1)] * len(grid), index=grid, columns=names)
    members = pd.DataFrame({"ticker":names,"start_date":index[0],"end_date":pd.NaT})
    t = np.arange(len(index), dtype=float)
    R = pd.DataFrame({name: 0.002*np.sin(t/7+i/3)+0.0001*(i-size/2)
                      for i, name in enumerate(names)}, index=index)
    target = _target(names, names[-size//5:], () if long_only else names[:size//5])
    expected = _daily_state_oracle(R, {d:target for d in grid}, 5.0)
    module = phase1 if long_only else phase0
    calls = _capture_native_statistics(monkeypatch, module)
    if long_only:
        expected -= _daily_state_oracle(R, {d:_target(names,names) for d in grid}, 0.0)
        out = module.long_only_tilt(R, sig, grid, members, top=0.2, n_trials=12)
        ci_key, prob_key = "active_sharpe_ci", "active_gt0_prob"
    else:
        out = module.quintile_ls(R, sig, grid, n_trials=12, membership=members)
        ci_key, prob_key = "sharpe_ci", "sharpe_gt0_prob"
    expected = expected.loc[grid[0]:grid[-1]]
    bc = calls["block_bootstrap_ci"][0]
    assert_series_equal(bc["args"][0], expected, check_names=False, atol=1e-12, rtol=1e-12)
    assert bc["kwargs"] == {"ann":252}
    assert bc["result"]["B"] == 5000 and bc["result"]["block"] == 21
    assert bc["result"]["n"] == len(expected)
    assert out[ci_key] == bc["result"]["sharpe_ci"]
    assert out[prob_key] == bc["result"]["sharpe_gt0_prob"]
    dsr = calls["deflated_sharpe"][0]
    assert dsr["kwargs"] == {"n_trials":12, "trading_year":252}
    assert out["dsr"] == dsr["result"]["dsr"]
    assert out["verdict"] == module.dsr_verdict(dsr["result"]["dsr"])


@pytest.mark.parametrize("results", [{}, {
    "adverse": {"active_sharpe":-0.4,"active_cum_pct":-5.0,"dsr":0.1,
                "verdict":"FAILS","active_sharpe_ci":[-1.0,-0.4,0.1],
                "active_gt0_prob":0.05,"port_sharpe":-0.3,"bench_sharpe":0.2},
}])
def test_phase1_report_does_not_substitute_historical_success_for_current_results(results):
    orth = {"corr_mom":0.9,"corr_size":0.8,"corr_rev":0.7,"ic_raw":{},"ic_orth":{}}
    grid = [pd.Timestamp("2025-01-31"),pd.Timestamp("2025-02-28")]
    rendered = phase1.render(results, orth, grid)
    assert "pending requalification" in rendered.lower()
    for historical in ("0.70–0.73", "0.997", "safe to add", "ship as", "robustly-positive"):
        assert historical not in rendered
    if results:
        assert "-0.4" in rendered and "FAILS" in rendered
