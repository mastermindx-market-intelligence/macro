"""R1-B matched-control pools: synthetic sessions only.  No market data is read."""
import json
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


def lens(rows, h="60m"):
    r = cell(rows, h)
    return (len(r["control_returns_a"]), len(r["control_returns_b"]))


S = sessions(13)


def test_pool_and_returns_follow_each_sessions_own_clock_and_prices():
    days, census = build(13)
    event = selected_event(S[0])
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


def test_null_sign_selected_event_is_no_control_without_calling_the_matcher(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("match_controls must not run")

    monkeypatch.setattr(pools.te, "match_controls", boom)
    days, census = build(13)
    for bad_sign in (None, True):
        event = selected_event(S[0], sign=0)
        if bad_sign is None:
            event = selected_event(S[0], sign=None)
        else:
            event = {**selected_event(S[0]), "qqq_open_to_decision_sign": True}
        pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
        assert pool["availability"] == "NO_CONTROL"
        assert pool["reason"] == "qqq_sign_unavailable"
        assert pool["matched_count"] == 0
        assert pool["matched_controls"] == []
    event_none = selected_event(S[0], sign=None)
    pool_none = pools.build_pool(event_none, census=census, config_bytes=CONFIG)
    rows = pools.measure_rows(event_none, pool_none, days, config_bytes=CONFIG, cache={})
    assert len(rows) == 12
    c = cell(rows)
    assert c["pool_availability"] == "NO_CONTROL"
    assert c["pool_reason"] == "qqq_sign_unavailable"
    assert c["control_returns_a"] == []
    assert c["control_returns_b"] == []
    assert isinstance(c["selected_return"], float)
    assert agg.event_delta(c, "L-A", floor=10) is None


def test_split_census_removes_and_counts_null_signs():
    days, census = build(13)
    extra = [census_row(S[0], sign=None), census_row(S[1], sign=None),
             {**census_row(S[2]), "qqq_open_to_decision_sign": True}]
    usable, rejected = pools.split_census(census + extra)
    assert len(usable) == 13
    assert rejected == 3
    usable[0]["symbol"] = "MUTATED"
    assert census[0]["symbol"] == SYMBOL


def test_pool_below_floor_has_no_controls_and_no_fallback():
    days, census = build(10)
    event = selected_event(sessions(10)[0])
    pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
    assert pool["matched_count"] == 9
    assert pool["availability"] == "NO_CONTROL"
    assert pool["reason"] == "matched_control_floor_not_met"
    assert pool["matched_controls"] == []
    assert pool["fallback_used"] is False
    rows = pools.measure_rows(event, pool, days, config_bytes=CONFIG, cache={})
    for r in rows:
        assert r["control_returns_a"] == []
        assert r["control_returns_b"] == []


def test_shift_bar_defects_censor_under_reading_b_only():
    days, census = build(13)
    key3 = (SYMBOL, S[3].isoformat())
    key4 = (SYMBOL, S[4].isoformat())
    f = days[key3]["stock_frame"]
    days[key3]["stock_frame"] = f.drop(f.index[7])
    f4 = days[key4]["stock_frame"].copy()
    f4.iloc[8, 4] = 0.0
    days[key4]["stock_frame"] = f4
    event = selected_event(S[0])
    pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
    rows = pools.measure_rows(event, pool, days, config_bytes=CONFIG, cache={})
    assert lens(rows) == (12, 10)
    assert agg.event_delta(cell(rows), "S-B", floor=10) is not None
    e0 = selected_event(S[0], selector="BASE_FRESH_LOW", delay=0)
    pool0 = pools.build_pool(e0, census=census, config_bytes=CONFIG)
    rows0 = pools.measure_rows(e0, pool0, days, config_bytes=CONFIG, cache={})
    assert lens(rows0) == (11, 11)


def test_control_with_a_missing_outcome_bar_is_absent_from_both_lists():
    days, census = build(13)
    key5 = (SYMBOL, S[5].isoformat())
    key6 = (SYMBOL, S[6].isoformat())
    f5 = days[key5]["stock_frame"]
    days[key5]["stock_frame"] = f5.drop(f5.index[12])
    f6 = days[key6]["stock_frame"]
    days[key6]["stock_frame"] = f6.drop(f6.index[40])
    event = selected_event(S[0])
    pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
    rows = pools.measure_rows(event, pool, days, config_bytes=CONFIG, cache={})
    for h in ("30m", "60m", "120m"):
        assert lens(rows, h) == (11, 11)
    assert lens(rows, "close") == (10, 10)


def test_control_event_uses_the_controls_own_session_inputs():
    days, census = build(13)
    event = selected_event(S[0])
    pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
    c2 = next(c for c in pool["matched_controls"] if c["session"] == S[2].isoformat())
    key2 = (SYMBOL, S[2].isoformat())
    days[key2]["normalization"]["prior_atr"] = 3.0
    days[key2]["normalization"]["prior_close"] = 105.0
    anchor = days[key2]["anchors"][c2["anchor_id"]]
    anchor["candidate_low"] = 97.0
    ce = pools.control_event(c2, day=days[key2], config_bytes=CONFIG)
    assert ce["selector"] == "BASE_FRESH_LOW"
    assert ce["prior_atr"] == 3.0
    assert ce["previous_regular_close"] == 105.0
    assert ce["candidate_low"] == 97.0
    assert ce["episode_low"] == 97.0
    assert pd.Timestamp(ce["decision_at"]) - pd.Timestamp(ce["candidate_at"]) == pd.Timedelta(minutes=10)
    assert pd.Timestamp(ce["entry_reference_at"]) - pd.Timestamp(ce["candidate_at"]) == pd.Timedelta(minutes=15)
    assert 98.8 not in (ce["candidate_low"], ce["episode_low"], ce.get("prior_atr"), ce.get("previous_regular_close"))


def test_control_clock_mismatch_is_refused():
    days, census = build(13)
    event = selected_event(S[0])
    pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
    c = dict(pool["matched_controls"][0])
    c["entry_reference_at"] = (
        pd.Timestamp(c["entry_reference_at"]) + pd.Timedelta(minutes=5)
    ).isoformat()
    key = (c["symbol"], c["session"])
    with pytest.raises(ValueError, match="control_entry_clock_mismatch"):
        pools.control_event(c, day=days[key], config_bytes=CONFIG)


def test_pool_event_identity_mismatch_is_refused():
    days, census = build(13)
    e0 = selected_event(S[0])
    pool0 = pools.build_pool(e0, census=census, config_bytes=CONFIG)
    e1 = selected_event(S[1])
    with pytest.raises(ValueError, match="pool_event_identity_mismatch"):
        pools.measure_rows(e1, pool0, days, config_bytes=CONFIG, cache={})


def test_control_without_beta_gives_no_return():
    days, census = build(13)
    key7 = (SYMBOL, S[7].isoformat())
    days[key7]["normalization"]["beta_available"] = False
    event = selected_event(S[0])
    pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
    rows = pools.measure_rows(event, pool, days, config_bytes=CONFIG, cache={})
    assert lens(rows) == (11, 11)


def test_each_control_outcome_is_computed_once(monkeypatch):
    calls = {"n": 0}
    orig = pools.te.measure_event_outcome

    def wrapped(*a, **k):
        calls["n"] += 1
        return orig(*a, **k)

    monkeypatch.setattr(pools.te, "measure_event_outcome", wrapped)
    days, census = build(13)
    cache = {}
    e0 = selected_event(S[0])
    pool0 = pools.build_pool(e0, census=census, config_bytes=CONFIG)
    pools.measure_rows(e0, pool0, days, config_bytes=CONFIG, cache=cache)
    assert calls["n"] == 156
    assert len(cache) == 144
    e1 = selected_event(S[1])
    pool1 = pools.build_pool(e1, census=census, config_bytes=CONFIG)
    pools.measure_rows(e1, pool1, days, config_bytes=CONFIG, cache=cache)
    assert calls["n"] == 180
    assert len(cache) == 156


def test_delta_is_the_same_at_every_cost():
    days, census = build(13)
    event = selected_event(S[0])
    pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
    rows = pools.measure_rows(event, pool, days, config_bytes=CONFIG, cache={})
    for h in ("30m", "60m", "120m", "close"):
        deltas = [agg.event_delta(cell(rows, h, c), "L-A", floor=10) for c in (10, 25, 50)]
        assert deltas[0] == pytest.approx(deltas[1], abs=1e-12)
        assert deltas[1] == pytest.approx(deltas[2], abs=1e-12)
    assert cell(rows, "60m", 10)["selected_return"] - cell(rows, "60m", 25)["selected_return"] == pytest.approx(
        0.0015, abs=1e-12)


def test_pools_digest_is_order_independent_and_content_sensitive():
    days, census = build(13)
    e0 = selected_event(S[0])
    e1 = selected_event(S[1])
    e2 = selected_event(S[2], selector="RECLAIM_ONLY", delay=1)
    p_ab = pools.build_pools([e0, e1, e2], census, config_bytes=CONFIG)
    p_ba = pools.build_pools([e2, e1, e0], census, config_bytes=CONFIG)
    assert pools.pools_digest(p_ab) == pools.pools_digest(p_ba)
    order = [(p["selector"], p["session"]) for p in p_ab]
    assert order == [
        ("EXHAUSTION_RECLAIM", S[0].isoformat()),
        ("EXHAUSTION_RECLAIM", S[1].isoformat()),
        ("RECLAIM_ONLY", S[2].isoformat()),
    ]
    p_short = pools.build_pools([e0, e1, e2], census[:-1], config_bytes=CONFIG)
    assert pools.pools_digest(p_ab) != pools.pools_digest(p_short)


def test_overlap_counts_selected_anchors_that_are_also_controls():
    days, census = build(13)
    e0 = selected_event(S[0], anchor_id=census[0]["anchor_id"])
    e1 = selected_event(S[1], anchor_id=census[1]["anchor_id"])
    built = pools.build_pools([e1, e0], census, config_bytes=CONFIG)
    assert pools.overlap(built) == {
        "EXHAUSTION_RECLAIM": {
            "selected_events": 2,
            "distinct_controls": 13,
            "selected_anchors_also_controls": 2,
            "pools_per_control": {"1": 2, "2": 11},
        }
    }


def test_other_symbols_census_rows_are_rejected_by_reason():
    days, census = build(13)
    census_ext = census + [census_row(d, symbol="NVDA") for d in S[1:]]
    event = selected_event(S[0])
    pool = pools.build_pool(event, census=census_ext, config_bytes=CONFIG)
    assert pool["excluded_counts"] == {"same_date": 1, "ticker": 12}
    assert pool["matched_count"] == 12


def test_sign_zero_matches_only_zero():
    days, census = build(13)
    census_m = [dict(r) for r in census]
    for i in range(1, 7):
        census_m[i] = {**census_m[i], "qqq_open_to_decision_sign": 1}
    event = selected_event(S[0], sign=0)
    pool = pools.build_pool(event, census=census_m, config_bytes=CONFIG)
    assert pool["availability"] == "NO_CONTROL"
    assert pool["matched_count"] == 6
    assert pool["excluded_counts"] == {"market_sign": 6, "same_date": 1}


def test_rows_feed_the_aggregate_module():
    days, census = build(13)
    event = selected_event(S[0])
    pool = pools.build_pool(event, census=census, config_bytes=CONFIG)
    rows = pools.measure_rows(event, pool, days, config_bytes=CONFIG, cache={})
    r = cell(rows)
    s = agg.cell_summary([r], "L-A", cfg=json.loads(CONFIG), with_interval=True)
    assert s["fires_raw"] == 1
    assert s["fires_delta"] == 1
    mean_a = sum(r["control_returns_a"]) / len(r["control_returns_a"])
    assert s["statistic"] == pytest.approx(r["selected_return"] - mean_a, abs=1e-15)


def test_same_control_at_a_different_delay_is_a_different_outcome():
    days, census = build(13)
    cache = {}
    e2 = selected_event(S[0])
    pool2 = pools.build_pool(e2, census=census, config_bytes=CONFIG)
    rows2 = pools.measure_rows(e2, pool2, days, config_bytes=CONFIG, cache=cache)
    e1 = selected_event(S[0], selector="RECLAIM_ONLY", delay=1)
    pool1 = pools.build_pool(e1, census=census, config_bytes=CONFIG)
    rows1 = pools.measure_rows(e1, pool1, days, config_bytes=CONFIG, cache=cache)
    expected = [(100 + slope(i) * 21) / (100 + slope(i) * 9) - 1 - 0.0025 for i in range(1, 13)]
    assert cell(rows1)["control_returns_a"] == pytest.approx(expected, abs=1e-15)
    assert len(cache) == 288
    assert cell(rows1)["control_returns_a"][0] != cell(rows2)["control_returns_a"][0]
