"""Manager-Quality Score: forward-return mechanics, market-adjustment, grading."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from engine import manager_quality as mq


def _closes(**series) -> pd.DataFrame:
    idx = pd.bdate_range("2025-01-01", periods=80)
    return pd.DataFrame({k: v for k, v in series.items()}, index=idx)


def test_forward_return_basic_and_horizon_guard():
    c = _closes(AAA=[100.0 + i for i in range(80)])      # +1/day
    # entry day 0, horizon 10 -> price 100 -> 110 = +10%
    r = mq.forward_return(c, "AAA", "2025-01-01", horizon=10)
    assert abs(r - 0.10) < 1e-6
    # horizon running past the data end -> None (never score an unfinished window)
    assert mq.forward_return(c, "AAA", c.index[-3].isoformat(), horizon=10) is None
    # unknown ticker -> None
    assert mq.forward_return(c, "ZZZ", "2025-01-01", horizon=5) is None


def test_market_forward_return_is_equal_weight_mean():
    c = _closes(A=[100.0 + i for i in range(80)],         # +10% over 10d from day0
                B=[100.0 + 2 * i for i in range(80)])      # +20% over 10d from day0
    m = mq.market_forward_return(c, "2025-01-01", 10, {})
    assert abs(m - 0.15) < 1e-6                            # (0.10 + 0.20)/2


def test_market_relative_excess_strips_beta():
    # A outruns the 2-name market; its excess is positive even in a rising tide.
    c = _closes(A=[100.0 + 2 * i for i in range(80)],
                B=[100.0 + i for i in range(80)])
    ret = mq.forward_return(c, "A", "2025-01-01", 10)
    bench = mq.market_forward_return(c, "2025-01-01", 10, {})
    assert ret - bench > 0


def test_blend_and_grade():
    assert mq._blend([0.1, 0.2], [0.0]) == pytest.approx(0.075)
    assert mq._blend([0.1], []) == pytest.approx(0.1)     # one-sided
    assert mq._blend([], []) is None
    assert mq._grade(1.0) == "A" and mq._grade(0.2) == "B"
    assert mq._grade(-0.2) == "C" and mq._grade(-1.0) == "D"
    assert mq._grade(None) == "n/a"


def test_compute_degrades_without_prices(monkeypatch):
    monkeypatch.setattr(mq, "load_closes", lambda: None)
    assert mq.compute_manager_quality() == {}


@pytest.mark.parametrize("gaps", [[1], list(range(10, 20)), [62]])
def test_interior_missing_prices_do_not_move_the_common_target(gaps):
    c = _closes(A=[100.0 + i for i in range(80)], B=[100.0 + i for i in range(80)])
    c.iloc[gaps, c.columns.get_loc("A")] = np.nan
    before = c.copy(deep=True)
    assert mq.forward_return(c, "A", "2025-01-01", 63) == pytest.approx(.63)
    assert mq.market_forward_return(c, "2025-01-01", 63) == pytest.approx(.63)
    pd.testing.assert_frame_equal(c, before)


def test_changes_after_the_target_cannot_change_the_measured_return():
    c = _closes(A=[100.0 + i for i in range(80)], B=[100.0 + i for i in range(80)])
    c.iloc[10:20, 0] = np.nan
    before = mq.forward_return(c, "A", "2025-01-01", 63)
    c.iloc[64:, 0] = 999.0
    assert before == pytest.approx(.63)
    assert mq.forward_return(c, "A", "2025-01-01", 63) == before


@pytest.mark.parametrize("entry,start", [("2024-12-31", 0), ("2025-01-05", 3)])
def test_non_session_entry_uses_the_same_panel_pair(entry, start):
    c = _closes(A=[100.0 + i for i in range(80)], B=[100.0 + i for i in range(80)])
    c.iloc[start + 1:start + 4, 0] = np.nan
    expected = (100.0 + start + 10) / (100.0 + start) - 1.0
    assert mq.forward_return(c, "A", entry, 10) == pytest.approx(expected)
    assert mq.market_forward_return(c, entry, 10) == pytest.approx(expected)


@pytest.mark.parametrize("endpoint", [0, 63])
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_unavailable_endpoint_is_withheld_without_a_replacement_quote(endpoint, bad):
    c = _closes(A=[100.0 + i for i in range(80)], B=[100.0 + i for i in range(80)])
    c.iloc[endpoint, 0] = bad
    assert mq.forward_return(c, "A", "2025-01-01", 63) is None
    assert mq.market_forward_return(c, "2025-01-01", 63) == pytest.approx(.63)


@pytest.mark.parametrize("p0,p1", [(0., 110.), (-1., 110.), (100., -1.),
                                    (np.nan, 110.), (100., np.nan),
                                    (np.inf, 110.), (100., np.inf)])
def test_benchmark_and_issuer_apply_the_same_endpoint_admission(p0, p1):
    c = _closes(A=[100.0 + i for i in range(80)], B=[100.0 + i for i in range(80)])
    c.iloc[0, 0], c.iloc[10, 0] = p0, p1
    assert mq.forward_return(c, "A", "2025-01-01", 10) is None
    assert mq.market_forward_return(c, "2025-01-01", 10) == pytest.approx(.10)
    assert mq.market_forward_return(c[["A"]], "2025-01-01", 10) is None


def test_observed_zero_exit_price_and_zero_horizon_remain_valid():
    c = _closes(A=[100.0 + i for i in range(80)], B=[100.0 + i for i in range(80)])
    c.iloc[10, 0] = 0.
    assert mq.forward_return(c, "A", "2025-01-01", 10) == -1.
    assert mq.market_forward_return(c, "2025-01-01", 10) == pytest.approx(-.45)
    assert mq.forward_return(c, "A", "2025-01-01", 0) == 0.
    assert mq.market_forward_return(c, "2025-01-01", 0) == 0.


@pytest.mark.parametrize("entry,horizon", [("2025-01-01", -1), ("2030-01-01", 63),
                                           ("not-a-date", 63)])
def test_no_valid_calendar_window_produces_no_return(entry, horizon):
    c = _closes(A=[100.0 + i for i in range(80)])
    assert mq.forward_return(c, "A", entry, horizon) is None
    assert mq.market_forward_return(c, entry, horizon) is None


def test_complete_and_masked_histories_agree_on_fixed_endpoint_returns():
    rng = np.random.default_rng(11017)
    dates = pd.bdate_range("2024-01-01", periods=100)
    for _ in range(32):
        values = 100. * np.cumprod(1. + rng.normal(.001, .01, (100, 3)), axis=0)
        c = pd.DataFrame(values, index=dates, columns=["A", "B", "C"])
        start, horizon = 5, 63
        expected = values[start + horizon] / values[start] - 1.
        assert mq.forward_return(c, "A", str(dates[start].date()), horizon) == pytest.approx(expected[0])
        assert mq.market_forward_return(c, str(dates[start].date()), horizon) == pytest.approx(expected.mean())
        c.iloc[rng.choice(np.arange(start + 1, start + horizon), 10, replace=False), 0] = np.nan
        assert mq.forward_return(c, "A", str(dates[start].date()), horizon) == pytest.approx(expected[0])
        assert mq.market_forward_return(c, str(dates[start].date()), horizon) == pytest.approx(expected.mean())


def _native_manager_case(monkeypatch, *, action="new", masked=False, missing_target=False):
    """Control only external prices/snapshots/maps; run all native calculations."""
    from engine import smart_money as sm
    from engine import stock_view

    dates = pd.bdate_range("2025-01-01", periods=100)
    tickers = [f"{slug.upper()}{i}" for slug in ("a", "b", "c") for i in range(8)]
    closes = pd.DataFrame({t: 100. + np.arange(100) for t in tickers}, index=dates)
    if masked:
        closes.loc[dates[10:20], [f"A{i}" for i in range(8)]] = np.nan
    if missing_target:
        closes.loc[dates[63], "A0"] = np.nan
    maps = {f"{i:09d}": t for i, t in enumerate(tickers, 1)}
    frames = {}
    for slug in ("a", "b", "c"):
        rows = [{"cusip": cusip, "issuer": ticker, "shares": 100., "value_usd": 10000.,
                 "sh_type": "SH", "period_end": "2024-12-31", "filing_date": "2025-01-01"}
                for cusip, ticker in maps.items() if ticker.startswith(slug.upper())]
        cur = pd.DataFrame(rows)
        prev = cur.iloc[0:0].copy() if action == "new" else cur.copy()
        if not prev.empty:
            prev["shares"] = 50. if action == "add" else 200.
            prev["period_end"], prev["filing_date"] = "2024-09-30", "2024-10-15"
        frames[slug] = (prev, cur)

    def snapshots(slug):
        prev, cur = frames[slug]
        return [("2024-09-30", "2024-10-15", prev), ("2024-12-31", "2025-01-01", cur)]

    for module in (mq, sm):
        monkeypatch.setattr(module, "_read_all", snapshots)
        monkeypatch.setattr(module, "name_ticker_map", lambda: {})
        monkeypatch.setattr(module, "full_cusip_map", lambda: (maps, {"synthetic": True}))
    monkeypatch.setattr(sm, "_read_period_pair", lambda slug, period: frames[slug])
    monkeypatch.setattr(mq, "load_closes", lambda: closes.copy())
    cfg = {"funds": {s: {"name": f"Synthetic fund {s.upper()}"} for s in ("a", "b", "c")}}
    direct = mq.compute_manager_quality(cfg)
    # Do not replace _safe_manager_quality: a swallowed error must not mimic a fix.
    payload = json.loads(json.dumps(sm.compute_smart_money(cfg), allow_nan=False))
    assert payload["manager_quality"] == direct and len(direct) == 3
    payload.pop("built")
    views = {t: stock_view._ev_ownership({"smart_money": rec})
             for t, rec in payload["by_ticker"].items()}
    return payload, views


@pytest.mark.parametrize("action", ["new", "add", "trim"])
def test_interior_gaps_cannot_create_native_grades_or_bilingual_quality_badges(monkeypatch, action):
    control, control_views = _native_manager_case(monkeypatch, action=action)
    masked, masked_views = _native_manager_case(monkeypatch, action=action, masked=True)
    assert masked == control
    assert masked_views == control_views
    for fund in masked["manager_quality"].values():
        assert fund["n_events"] == 8 and fund["grade"] == "n/a"
        assert fund["quality_raw"] == pytest.approx(0.)
    for rec in masked["by_ticker"].values():
        assert "quality_cluster" not in rec
        assert all("fund_grade" not in h for h in rec["holders"])
    for view in masked_views.values():
        assert view and "top-grade" not in view["value"]
        assert "高评级" not in view["value_zh"]


def test_missing_target_preserves_the_event_floor_through_the_actual_consumer(monkeypatch):
    payload, views = _native_manager_case(monkeypatch, missing_target=True)
    fund = payload["manager_quality"]["a"]
    assert fund["n_events"] == 7 and fund["grade"] == "n/a"
    assert fund["quality_z"] is None
    assert "quality_cluster" not in payload["by_ticker"]["A0"]
    assert "top-grade" not in views["A0"]["value"] and "高评级" not in views["A0"]["value_zh"]
