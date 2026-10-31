"""Synthetic EOD acceptance for the display-only tech-volatility-shock module."""
from __future__ import annotations

import math
from datetime import date, datetime, timezone

import pandas as pd

from engine.tech_volatility_shock import build_snapshot, snapshot_from_bars
from lib import nyse_calendar


NOW = datetime(2026, 10, 31, 1, 0, tzinfo=timezone.utc)  # Fri Oct 30 21:00 ET


def _frames(n: int = 110) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = nyse_calendar.sessions_between(date(2026, 4, 1), date(2026, 10, 30))[-n:]
    assert len(dates) == n and dates[-1] == date(2026, 10, 30)
    idx = pd.DatetimeIndex(dates)
    def make(seed: int, final_return: float, final_gap: float, final_vol: float):
        rows = []
        prev = 100.0
        for i, d in enumerate(dates):
            delta = math.sin((i + seed) / 5.0) * (0.003 if seed == 0 else 0.005)
            if i == len(dates) - 1:
                delta = final_return
            op = prev * (1 + (final_gap if i == len(dates) - 1 else delta * 0.5))
            cl = prev * (1 + delta)
            rows.append((op, cl, 1_000_000.0 * (final_vol if i == len(dates) - 1 else 1.0)))
            prev = cl
        return pd.DataFrame(rows, columns=["open", "close", "volume"], index=idx)
    return make(0, -0.0177, -0.0104, 2.07), make(3, -0.0347, -0.0253, 2.32)


def test_screenshot_shape_uses_actual_math_without_hardcoding():
    spy, qqq = _frames()
    snap = snapshot_from_bars(spy, qqq, now=NOW)
    assert snap["status"] == "ok"
    assert snap["asof"] == "2026-10-30"
    assert snap["lag_sessions"] == 0
    assert snap["relative_pp"] == -1.70
    assert snap["relative_z60"] is not None
    assert snap["session_read"] == "overnight_dominant"
    s, q = snap["indices"]
    assert (s["symbol"], q["symbol"]) == ("SPY", "QQQ")
    assert (s["return_pct"], q["return_pct"]) == (-1.77, -3.47)
    assert s["volume_multiple"] == 2.07
    assert q["volume_multiple"] == 2.32
    assert s["overnight_pct"] == -1.04 and q["overnight_pct"] == -2.53
    assert s["rank_ytd"] == 1 and q["rank_ytd"] == 1
    # The intraday leg is a price ratio; summing rounded legs is NOT the invariant.
    for raw, row in ((spy, s), (qqq, q)):
        op, cl = raw.iloc[-1]["open"], raw.iloc[-1]["close"]
        prev = raw.iloc[-2]["close"]
        assert math.isclose((op / prev) * (cl / op) - 1, cl / prev - 1)
        assert row["intraday_pct"] == round((cl / op - 1) * 100, 2)


def test_causal_z_excludes_current_extreme():
    spy, qqq = _frames()
    baseline = snapshot_from_bars(spy, qqq, now=NOW)
    prior = spy["close"].pct_change(fill_method=None).iloc[-61:-1]
    expected = (spy["close"].pct_change(fill_method=None).iloc[-1] - prior.mean()) / prior.std(ddof=1)
    assert baseline["indices"][0]["z60"] == round(float(expected), 2)
    spy2 = spy.copy()
    spy2.loc[spy2.index[-1], "close"] *= 0.9
    changed = snapshot_from_bars(spy2, qqq, now=NOW)
    newret = spy2["close"].iloc[-1] / spy2["close"].iloc[-2] - 1
    assert changed["indices"][0]["z60"] == round(float((newret - prior.mean()) / prior.std(ddof=1)), 2)


def test_mismatch_missing_open_and_no_data_refuse():
    spy, qqq = _frames()
    assert snapshot_from_bars(spy, qqq.iloc[:-1], now=NOW)["status"] == "unavailable"
    assert snapshot_from_bars(spy, qqq.drop(columns=["open"]), now=NOW)["status"] == "unavailable"
    assert snapshot_from_bars(None, None, now=NOW)["indices"] == []
    assert snapshot_from_bars(spy, qqq.assign(open=0), now=NOW)["status"] == "unavailable"


def test_insufficient_history_keeps_returns_but_nulls_z_and_volume():
    spy, qqq = _frames()
    snap = snapshot_from_bars(spy.iloc[-15:], qqq.iloc[-15:], now=NOW)
    assert snap["status"] == "partial"
    assert snap["relative_pp"] == -1.70
    assert snap["relative_z60"] is None
    assert all(x["z60"] is None and x["volume_multiple"] is None for x in snap["indices"])


def test_missing_interior_session_cannot_create_a_multiday_return():
    spy, qqq = _frames()
    mid = spy.index[-23]
    spy = spy.drop(mid)
    qqq = qqq.drop(mid)
    snap = snapshot_from_bars(spy, qqq, now=NOW)
    assert snap["status"] == "partial"
    assert snap["indices"][0]["z60"] is None
    assert snap["relative_z60"] is None


def test_stale_day_and_early_partial_bar_not_misrepresented():
    spy, qqq = _frames()
    later = datetime(2026, 11, 4, 2, 0, tzinfo=timezone.utc)  # Nov 3 after close
    snap = snapshot_from_bars(spy, qqq, now=later)
    assert snap["status"] == "stale" and snap["lag_sessions"] == 2
    before_close = datetime(2026, 10, 30, 19, 30, tzinfo=timezone.utc)
    assert snapshot_from_bars(spy, qqq, now=before_close)["status"] == "unavailable"


def test_mixed_sign_legs_do_not_assert_preopen_damage():
    spy, qqq = _frames()
    spy.loc[spy.index[-1], "open"] = spy["close"].iloc[-2] * 1.005
    snap = snapshot_from_bars(spy, qqq, now=NOW)
    assert snap["session_read"] == "mixed"
    assert snap["indices"][0]["overnight_share"] is None


def test_volume_not_from_adjusted_yahoo_and_missing_volume_truthful():
    spy, qqq = _frames()
    spy = spy.drop(columns=["volume"])
    snap = snapshot_from_bars(spy, qqq, now=NOW)
    assert snap["status"] == "partial"
    assert snap["indices"][0]["volume_multiple"] is None
    assert snap["indices"][1]["volume_multiple"] == 2.32
    assert snap["volume_scope"] == "full_market_day"


def test_reader_handles_unrestored_r2_without_network_or_fake_values(monkeypatch):
    monkeypatch.setattr("engine.tech_volatility_shock.store.read", lambda group, sym: None)
    snap = build_snapshot(now=NOW)
    assert snap["status"] == "unavailable"
    assert snap["relative_pp"] is None
