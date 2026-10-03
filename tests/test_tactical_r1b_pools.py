"""R1-B matched-control pools: synthetic sessions only.  No market data is read."""
from datetime import date, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.entry_radar import tactical_exhaustion as te
from engine.session_digest import session_window_et
from lib.nyse_calendar import is_session
from scripts.research import terminal_tactical_r1b_aggregate as agg
from scripts.research import terminal_tactical_r1b_pools as pools

CONFIG = (Path(__file__).resolve().parents[1] / "research/species/tti_r1b/config_v4.json").read_bytes()
SYMBOL = "AMD"
COLUMNS = ["open", "high", "low", "close", "volume"]


def sessions(n, first=date(2026, 3, 2)):
    out, day = [], first
    while len(out) < n:
        if is_session(day):
            out.append(day)
        day += timedelta(days=1)
    return out


def slope(i):
    return 0.01 * (i + 1)


def frames(day, s):
    """Stock bar k opens at 100 + s*k and closes at 100 + s*(k+1); the benchmark is flat."""
    start, close = session_window_et(day)
    index = pd.date_range(start, close - pd.Timedelta(minutes=5), freq="5min")
    stock = pd.DataFrame(
        [[100 + s * k, 100 + s * (k + 1) + 0.05, 100 + s * k - 0.05, 100 + s * (k + 1), 1000.0]
         for k in range(len(index))], index=index, columns=COLUMNS)
    qqq = pd.DataFrame([[100.0, 100.1, 99.9, 100.0, 1000.0] for _ in index],
                       index=index, columns=COLUMNS)
    return stock, qqq


def census_row(day, *, minutes=35, sign=0, bucket=1, displacement=0.8, symbol=SYMBOL):
    """One control-census row; `minutes` after the 09:30 open (35 -> 10:05 ET, clock bin 20)."""
    start, _ = session_window_et(day)
    at = (start + timedelta(minutes=minutes)).astimezone(timezone.utc).isoformat()
    return {"anchor_id": f"{symbol}:{day.isoformat()}:{at}", "candidate_at": at,
            "symbol": symbol, "session": day.isoformat(),
            "clock_bin": (570 + minutes) // 30, "displacement_bucket": bucket,
            "displacement_atr": displacement, "future_family_labels_used": False,
            "qqq_open_to_decision_sign": sign}


def build(n=13):
    """n consecutive sessions of one symbol: day store plus one census row per session."""
    days, census = {}, []
    for i, day in enumerate(sessions(n)):
        stock, qqq = frames(day, slope(i))
        row = census_row(day)
        census.append(row)
        days[(SYMBOL, day.isoformat())] = {
            "stock_frame": stock, "benchmark_frame": qqq,
            "normalization": {"availability": "AVAILABLE", "prior_atr": 2.0, "prior_close": 101.0,
                              "beta_available": True, "beta": 1.0},
            "anchors": {row["anchor_id"]: {"anchor_id": row["anchor_id"],
                                           "candidate_at": row["candidate_at"], "candidate_low": 99.0}},
        }
    return days, census


def selected_event(day, *, selector="EXHAUSTION_RECLAIM", delay=2, minutes=30, sign=0, anchor_id=None):
    """A selected event whose candidate is `minutes` after the open (30 -> 10:00 ET, clock bin 20)."""
    start, _ = session_window_et(day)
    candidate = start + timedelta(minutes=minutes)
    decision = candidate + timedelta(minutes=5 * delay)
    return {"selector": selector,
            "anchor_id": anchor_id or f"{SYMBOL}:{day.isoformat()}:sel:{selector}:{minutes}",
            "candidate_at": candidate.astimezone(timezone.utc).isoformat(),
            "decision_at": decision.astimezone(timezone.utc).isoformat(),
            "entry_reference_at": (decision + timedelta(minutes=5)).astimezone(timezone.utc).isoformat(),
            "confirmation_delay_bars": delay, "processing_latency_minutes": 5,
            "candidate_low": 99.0, "episode_low": 98.8, "prior_atr": 2.0,
            "previous_regular_close": 101.0, "displacement_atr": 0.8,
            "symbol": SYMBOL, "session": day.isoformat(),
            "qqq_open_to_decision_sign": sign, "beta": 1.0, "market_outcomes_computed": False}


def cell(rows, horizon="60m", cost=25):
    return next(r for r in rows if r["horizon"] == horizon and r["cost_bps"] == cost)


def test_pool_and_returns_follow_each_sessions_own_clock_and_prices():
    days, census = build(13)
    days_list = sessions(13)
    event = selected_event(days_list[0])
    pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
    assert (pool["availability"], pool["matched_count"]) == ("AVAILABLE", 12)
    assert pool["excluded_counts"] == {"same_date": 1}
    assert pool["market_outcomes_computed"] is False and pool["fallback_used"] is False
    rows = pools.measure_rows(event, pool, days, config_bytes=CONFIG, cache={})
    assert len(rows) == 12
    row = cell(rows)
    # selected: candidate 10:00, two confirmation bars, entry 10:15 = bar 9; 60 minutes = bars 9..20
    s0 = slope(0)
    assert row["selected_return"] == pytest.approx((100 + s0 * 21) / (100 + s0 * 9) - 1 - 0.0025, abs=1e-15)
    # each control: candidate 10:05 on ITS day, same two-bar delay, entry 10:20 = bar 10; bars 10..21
    expected = [(100 + slope(i) * 22) / (100 + slope(i) * 10) - 1 - 0.0025 for i in range(1, 13)]
    assert row["control_returns_a"] == pytest.approx(expected, abs=1e-15)
    assert row["control_returns_b"] == row["control_returns_a"]
    assert (row["candidate_bin"], row["decision_bin"]) == (20, 20)
