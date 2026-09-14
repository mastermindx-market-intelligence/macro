"""Generic baskets compute core (engine.baskets_region.compute_region_baskets) + the HK and
Canada wrappers that load their data plane and delegate into it.

The core is a pure function (closes, membership, benchmark, proxy_reader, name_key) reused by
the China / Hong Kong / Canada pages, so the shared invariants are tested once here: thin
baskets skipped, members outside the cache surfaced in `missing`, removed members drop from
the latest roster, rel == ret − benchmark at a horizon, the CHART matrix is well-formed,
late-listing members flagged `partial`, the configurable name_key selects the display name,
the etf_proxy cross-check runs through the injected reader, and it degrades to None. Two thin
wrapper tests confirm baskets_hk / baskets_canada load + delegate with the right benchmark.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import baskets_canada as bkca
from engine import baskets_hk as bkhk
from engine import baskets_region as reg


def _frame(tickers, n=180, start="2025-01-02"):
    idx = pd.date_range(start, periods=n, freq="B")
    rng = np.random.default_rng(1)
    data = {t: 100 * np.cumprod(1 + rng.normal(0.0005, 0.01, n)) for t in tickers}
    return pd.DataFrame(data, index=idx), idx


def _bench(idx):
    return pd.DataFrame({"close": 400 * (1.0006 ** np.arange(len(idx))), "volume": np.ones(len(idx))}, index=idx)


def _mem(members, **top):
    base = {"baskets": members, "benchmark_label": "BENCH", "benchmark_label_zh": "基准"}
    base.update(top)
    return base


def test_core_pit_missing_rel_chart_and_namekey():
    closes, idx = _frame(["A", "B", "C", "D"])
    members = {
        "t1": {"name": "One", "name_zh": "一", "category": "Cat", "category_zh": "类", "etf_proxy": None,
               "created": "2025-01-02", "thesis": "x", "thesis_zh": "甲", "members": [
                   {"ticker": "A", "added": "2025-01-02", "name": "AceCorp", "name_zh": "甲公司", "rationale": "ra"},
                   {"ticker": "B", "added": "2025-01-02", "name": "BeeCorp", "name_zh": "乙公司", "rationale": "rb"},
                   {"ticker": "C", "added": "2025-01-02", "name": "CeeCorp", "name_zh": "丙公司", "rationale": "rc"},
                   {"ticker": "Z", "added": "2025-01-02", "name": "Zed", "rationale": "rz"}]},  # not in cache
        "thin": {"name": "Thin", "category": "Cat", "created": "2025-01-02", "members": [
            {"ticker": "A", "added": "2025-01-02"}, {"ticker": "B", "added": "2025-01-02"}]},
    }
    bench = _bench(idx)
    out = reg.compute_region_baskets(closes, _mem(members), bench, lambda s: None, name_key="name")
    assert [b["id"] for b in out["baskets"]] == ["t1"]                 # thin (<3) skipped
    b = out["baskets"][0]
    assert b["n_members"] == 3 and b["missing"] == ["Z"]
    assert {m["name"] for m in b["members"]} == {"AceCorp", "BeeCorp", "CeeCorp"}   # name_key='name'
    br = bench["close"].iloc[-1] / bench["close"].iloc[-21] - 1
    assert abs(b["perf"]["20d"]["rel"] - (b["perf"]["20d"]["ret"] - br)) < 1e-6     # rel == ret − bench
    c = out["chart"]
    assert len(c["dates"]) == 180 and len(c["bench"]) == 180 and len(c["baskets"]["t1"]) == 180
    assert out["benchmark_label"] == "BENCH" and out["categories_zh"] == ["类"]

    # same membership, name_key='name_zh' surfaces the Chinese display name instead
    out2 = reg.compute_region_baskets(closes, _mem(members), bench, lambda s: None, name_key="name_zh")
    assert {m["name"] for m in out2["baskets"][0]["members"]} == {"甲公司", "乙公司", "丙公司"}


def test_core_removed_and_partial():
    closes, idx = _frame(["A", "B", "C", "D"], n=400, start="2024-01-01")
    closes.loc[closes.index[:300], "D"] = np.nan        # D only lists for the last 100 sessions
    members = {"t": {"name": "T", "category": "C", "created": "2024-01-01", "members": [
        {"ticker": "A", "added": "2024-01-01"}, {"ticker": "B", "added": "2024-01-01"},
        {"ticker": "C", "added": "2024-01-01", "removed": "2024-06-01"},   # removed → drops from roster
        {"ticker": "D", "added": "2024-01-01"}]}}                          # late tape → partial
    out = reg.compute_region_baskets(closes, _mem(members), _bench(idx), lambda s: None)
    b = out["baskets"][0]
    assert "C" not in {m["symbol"] for m in b["members"]}                 # removed member gone
    assert "D" in {p["symbol"] for p in b["partial"]}                     # late-lister flagged
    assert "A" not in {p["symbol"] for p in b["partial"]}


def test_core_pre_window_add_not_partial():
    """`added` dates that predate the rolling calendar must not flag the whole basket partial
    once the window rolls past them (same window-clamp as engine/baskets.py) — only the
    genuinely-late tape is flagged."""
    closes, idx = _frame(["A", "B", "C", "D"], n=400, start="2024-01-01")
    closes.loc[closes.index[:300], "D"] = np.nan        # D's tape genuinely starts mid-window
    members = {"t": {"name": "T", "category": "C", "created": "2022-01-03", "members": [
        {"ticker": t, "added": "2022-01-03"} for t in "ABCD"]}}          # all added pre-window
    out = reg.compute_region_baskets(closes, _mem(members), _bench(idx), lambda s: None)
    assert {p["symbol"] for p in out["baskets"][0]["partial"]} == {"D"}


def test_core_reference_via_injected_reader():
    closes, idx = _frame(["A", "B", "C"])
    etf = pd.DataFrame({"close": 50 * np.cumprod(1 + np.random.default_rng(2).normal(0, 0.01, len(idx)))}, index=idx)
    members = {"t": {"name": "T", "category": "C", "created": "2025-01-02", "etf_proxy": "XYZ.TO",
                     "etf_proxy_note": "proxy", "members": [
                         {"ticker": "A", "added": "2025-01-02"}, {"ticker": "B", "added": "2025-01-02"},
                         {"ticker": "C", "added": "2025-01-02"}]}}
    out = reg.compute_region_baskets(closes, _mem(members), _bench(idx),
                                     lambda s: etf if s == "XYZ.TO" else None)
    ref = out["baskets"][0]["reference"]
    assert ref is not None and ref["label"] == "XYZ.TO" and "corr" in ref and "rel_corr" in ref


def test_core_degrades():
    closes, idx = _frame(["A", "B", "C"])
    good = {"t": {"name": "T", "category": "C", "members": [
        {"ticker": "A", "added": "2025-01-02"}, {"ticker": "B", "added": "2025-01-02"},
        {"ticker": "C", "added": "2025-01-02"}]}}
    assert reg.compute_region_baskets(closes, None, _bench(idx), lambda s: None) is None        # no membership
    assert reg.compute_region_baskets(None, _mem(good), _bench(idx), lambda s: None) is None     # no closes
    assert reg.compute_region_baskets(closes, _mem(good), None, lambda s: None) is None          # no benchmark


def _wrapper_check(monkeypatch, mod, bench_sym, label):
    closes, idx = _frame(["AAA", "BBB", "CCC"])
    bench = _bench(idx)
    members = {"t": {"name": "T", "name_zh": "T", "category": "C", "category_zh": "类", "created": "2025-01-02",
                     "members": [{"ticker": "AAA", "added": "2025-01-02", "name": "Aaa"},
                                 {"ticker": "BBB", "added": "2025-01-02", "name": "Bbb"},
                                 {"ticker": "CCC", "added": "2025-01-02", "name": "Ccc"}]}}
    mem = _mem(members, benchmark=bench_sym, benchmark_label=label)
    monkeypatch.setattr(mod, "_closes", lambda: closes)
    monkeypatch.setattr(mod, "_membership", lambda: mem)
    monkeypatch.setattr(mod.store, "read", lambda g, n: bench if n == bench_sym else None)
    return mem


def test_hk_wrapper_delegates(monkeypatch):
    _wrapper_check(monkeypatch, bkhk, "_HSI", "HSI")
    out = bkhk.compute_hk_baskets()
    assert out is not None and out["benchmark_label"] == "HSI" and out["baskets"][0]["n_members"] == 3
    assert {m["name"] for m in out["baskets"][0]["members"]} == {"Aaa", "Bbb", "Ccc"}   # name_key='name'


def test_canada_wrapper_delegates(monkeypatch):
    _wrapper_check(monkeypatch, bkca, "XIC.TO", "S&P/TSX")
    out = bkca.compute_canada_baskets()
    assert out is not None and out["benchmark_label"] == "S&P/TSX" and out["baskets"][0]["n_members"] == 3


# Observation metadata does not replace or recompute the existing return series.
def test_member_weekly_dates_distinguish_current_gap_and_stale_prices():
    closes, idx = _frame(["A", "B", "C", "D"])
    closes.loc[idx[-1], "B"] = np.nan
    closes.loc[idx[-3], "C"] = np.nan
    members = {"t": {"name": "T", "category": "C", "members": [
        {"ticker": t, "added": "2025-01-02"} for t in "ABCD"]}}
    out = reg.compute_region_baskets(closes, _mem(members), _bench(idx), lambda _: None)
    rows = {m["symbol"]: m for m in out["baskets"][0]["members"]}
    today = idx[-1].strftime("%Y-%m-%d")
    assert rows["A"]["price_asof"] == rows["A"]["ret_5d_asof"] == today
    assert rows["B"]["price_asof"] == idx[-2].strftime("%Y-%m-%d")
    assert rows["B"]["ret_5d_asof"] is None
    assert rows["C"]["price_asof"] == today and rows["C"]["ret_5d_asof"] is None
    assert rows["D"]["ret_5d_asof"] == today
    for ticker, row in rows.items():
        expected = reg._trailing_return(closes[ticker].dropna(), 5)
        assert row["ret_5d"] == round(expected, 4)


def test_weekly_date_requires_six_complete_daily_observations():
    import pytest
    idx = pd.bdate_range("2026-08-25", periods=10)
    series = pd.Series(np.arange(10) + 100.0, index=idx)
    assert reg._member_price_dates(series)["ret_5d_asof"] == "2026-09-07"
    assert reg._member_price_dates(series.iloc[-5:])["ret_5d_asof"] is None
    for value in [np.nan, 0.0, -1.0, float("inf"), True, np.bool_(True), "100", 10**400]:
        bad = series.astype(object)
        bad.iloc[-3] = value
        assert reg._member_price_dates(bad)["ret_5d_asof"] is None
    assert reg._member_price_dates(series.iloc[::-1])["ret_5d_asof"] is None
    duplicate = pd.concat([series, series.iloc[-1:]])
    assert reg._member_price_dates(duplicate)["ret_5d_asof"] is None
    intraday = series.copy()
    intraday.index = intraday.index + pd.Timedelta(hours=14)
    assert reg._member_price_dates(intraday)["ret_5d_asof"] is None
    before = series.copy(deep=True)
    reg._member_price_dates(series)
    pd.testing.assert_series_equal(series, before)


def test_old_price_is_not_relabelled_with_the_snapshot_date():
    idx = pd.bdate_range("2026-08-25", periods=10)
    series = pd.Series(np.arange(10) + 100.0, index=idx)
    series.iloc[-2:] = np.nan
    dates = reg._member_price_dates(series)
    assert dates["price_asof"] == idx[-3].strftime("%Y-%m-%d")
    assert dates["ret_5d_asof"] is None
    empty = reg._member_price_dates(series * np.nan)
    assert empty == {"price_asof": None, "ret_5d_asof": None}
