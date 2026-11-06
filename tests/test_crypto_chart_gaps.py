"""Crypto producer-to-renderer gaps without changing dated breadth inputs."""
from __future__ import annotations

import math
import re

import pandas as pd

from scripts import build_crypto as C


def _row(as_of, **updates):
    row = {
        "symbol": "BTC", "as_of": str(as_of.date()), "state": "Range",
        "price": 12345.0, "change_24h": 2.0, "change_30d": 8.0,
        "history_days": 4, "history_chip": "Building",
        "spark_dates": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        "spark_values": [10.0, 11.0, 12.0, 13.0],
    }
    row.update(updates)
    return row


def _store(monkeypatch, coinbase, yahoo=None):
    def read(group, name):
        if (group, name) == ("coinbase", "btc_daily"):
            return coinbase
        if (group, name) == ("yahoo", "BTC-USD"):
            return yahoo
        return pd.DataFrame()
    monkeypatch.setattr(C.store, "read", read)


def test_missing_prices_reach_renderer_without_advancing_dated_snapshot(monkeypatch):
    dates = pd.date_range("2026-01-01", periods=40)
    values = [float(100 + i) for i in range(40)]
    for i, value in [(8, math.nan), (9, math.inf), (10, 0), (11, -1), (38, math.nan)]:
        values[i] = value
    values[39] = 999999.0  # Future data must not advance this dated snapshot.
    _store(monkeypatch, pd.DataFrame({"close": values}, index=dates))
    row = C._enrich_universe([_row(dates[38])])[0]
    assert row["spark_dates"] == [str(d.date()) for d in dates[:39]]
    assert [i for i, v in enumerate(row["spark_values"]) if v is None] == [8, 9, 10, 11, 38]
    assert row["spark_values"][-2] == 137.0
    assert row["history_days"] == 34
    assert row["history_chip"] == "34D"
    assert row["as_of"] == str(dates[38].date())
    assert row["price"] == 12345.0 and row["change_30d"] == 8.0
    assert 'data-gap-count="5"' in row["spark"]
    assert "Latest missing" in row["spark"]
    assert "最新值缺失" in row["spark"]
    assert str(dates[37].date()) in row["spark"]
    path = re.search(r'class="ilx-path" d="([^"]+)"', row["spark"]).group(1)
    assert path.count("M") == 2
    assert "999999" not in row["spark"]


def test_window_keeps_ninety_observations_plus_missing_slots(monkeypatch):
    dates = pd.date_range("2026-01-01", periods=121)
    values = [float(100 + i) for i in range(121)]
    for i in (30, 70, 119, 120):
        values[i] = math.nan
    series = pd.Series(values, index=dates)
    _store(monkeypatch, series.to_frame("close"))
    row = C._enrich_universe([_row(dates[-1])])[0]
    observed = series.dropna().tail(90)
    expected = series.loc[observed.index[0]:]
    assert row["spark_dates"] == [str(d.date()) for d in expected.index]
    assert len(row["spark_values"]) == 94
    assert sum(v is not None for v in row["spark_values"]) == 90
    assert row["spark_values"][-2:] == [None, None]
    assert row["history_days"] == 90 and row["history_chip"] == "90D"
    assert 'data-gap-count="4"' in row["spark"]
    assert "Latest missing" in row["spark"]


def test_all_missing_coinbase_still_uses_yahoo_with_gaps(monkeypatch):
    dates = pd.date_range("2026-01-01", periods=35)
    yahoo = pd.DataFrame({"close_price": [float(100 + i) for i in range(35)]}, index=dates)
    yahoo.iloc[17, 0] = math.nan
    yahoo.iloc[-1, 0] = math.nan
    coinbase = pd.DataFrame({"close": [math.nan] * 35}, index=dates)
    _store(monkeypatch, coinbase, yahoo)
    row = C._enrich_universe([_row(dates[-1])])[0]
    assert len(row["spark_dates"]) == 35
    assert row["spark_values"][17] is None and row["spark_values"][-1] is None
    assert row["history_days"] == 33
    assert 'data-gap-count="2"' in row["spark"]


def test_missing_slots_do_not_satisfy_thirty_observation_admission(monkeypatch):
    dates = pd.date_range("2026-01-01", periods=35)
    frame = pd.DataFrame({"close": [100.0] * 29 + [math.nan] * 6}, index=dates)
    _store(monkeypatch, frame)
    original = _row(dates[-1])
    row = C._enrich_universe([dict(original)])[0]
    for field in ("spark_dates", "spark_values", "history_days", "history_chip"):
        assert row[field] == original[field]


def test_other_series_consumers_keep_existing_clean_contract(monkeypatch):
    dates = pd.date_range("2026-01-01", periods=4)
    _store(monkeypatch, pd.DataFrame({"close": [100, "bad", None, 103]}, index=dates))
    clean = C._series("coinbase", "btc_daily")
    slots = C._series("coinbase", "btc_daily", preserve_missing=True)
    assert list(clean.index) == [dates[0], dates[3]]
    assert list(clean) == [100, 103]
    assert list(slots.index) == list(dates)
    assert slots.isna().tolist() == [False, True, True, False]


def test_complete_history_retains_existing_chart_and_breadth_fields(monkeypatch):
    dates = pd.date_range("2026-01-01", periods=120)
    values = [float(100 + i) for i in range(120)]
    _store(monkeypatch, pd.DataFrame({"close": values}, index=dates))
    row = C._enrich_universe([_row(dates[-1])])[0]
    payload = {"dates": [str(d.date()) for d in dates[-90:]], "vals": values[-90:]}
    assert row["spark"] == C.illus(payload, kind="line", accent="var(--tone)", height=42,
                                  max_points=50, value_fmt="{:,.3g}",
                                  aria_en="BTC available price history")
    assert row["history_days"] == 90 and row["history_chip"] == "90D"


def test_existing_snapshot_zero_reaches_shared_renderer(monkeypatch):
    _store(monkeypatch, pd.DataFrame())
    row = _row(pd.Timestamp("2026-01-04"), symbol="OTHER", spark_values=[10.0, 11.0, 12.0, 0.0])
    result = C._enrich_universe([row])[0]
    assert result["spark_values"][-1] == 0.0
    assert "ilx-historical" not in result["spark"]
    assert 'data-gap-count=' not in result["spark"]
