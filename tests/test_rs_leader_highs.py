"""Point-in-time and missingness tests for Leader Radar RS-high read-only lens."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from engine.rs_leader_highs import observe_rs_highs
from lib.nyse_calendar import sessions_between, last_session_on_or_before


def _source(end=date(2026, 10, 9), n=390):
    sessions = sessions_between(end - timedelta(days=700), end)[-n:]
    idx = pd.to_datetime(sessions)
    bench = pd.Series(np.linspace(100.0, 120.0, len(idx)), index=idx)
    ratio = pd.Series(np.linspace(0.9, 1.1, len(idx)), index=idx)
    stock = bench * ratio
    return stock, bench


def test_daily_and_completed_weekly_rs_highs_true_but_price_not_required():
    stock, bench = _source()
    bench = pd.Series(np.linspace(160, 100, len(bench)), index=bench.index)
    stock = bench * np.linspace(0.9, 1.1, len(bench))
    got = observe_rs_highs(stock, bench, as_of=date(2026, 10, 9))
    assert got["daily"]["new_high"] is True
    assert got["weekly"]["new_high"] is True
    assert got["daily"]["price_new_high"] is False
    assert got["daily"]["rs_leads_price"] is True
    assert got["weekly"]["rs_leads_price"] is True


def test_no_lookahead_future_price_or_benchmark():
    stock, bench = _source()
    cut = date(2026, 10, 7)
    first = observe_rs_highs(stock, bench, as_of=cut)
    assert first["weekly"]["as_of"] == "2026-10-02"
    altered = stock.copy()
    altered.loc["2026-10-08":] = altered.loc["2026-10-08":] * 50
    second = observe_rs_highs(altered, bench, as_of=cut)
    assert first == second


def test_strict_high_equality_is_not_a_new_high():
    stock, bench = _source()
    ratio = stock / bench
    stock.iloc[-1] = float(ratio.iloc[-2]) * bench.iloc[-1]
    daily = observe_rs_highs(stock, bench, as_of=date(2026, 10, 9))["daily"]
    assert daily["new_high"] is False


def test_missing_benchmark_last_session_is_unknown_not_false():
    stock, bench = _source()
    bench.iloc[-1] = np.nan
    got = observe_rs_highs(stock, bench, as_of=date(2026, 10, 9))
    assert got["daily"]["new_high"] is None
    assert got["weekly"]["new_high"] is None
    assert got["daily"]["reason"] == "source_gap_or_nonpositive_close"


def test_missing_week_last_session_refuses_both_horizons():
    stock, bench = _source()
    missing = last_session_on_or_before(date(2026, 4, 10))
    stock = stock.drop(pd.Timestamp(missing))
    got = observe_rs_highs(stock, bench, as_of=date(2026, 10, 9))
    assert got["daily"]["new_high"] is None
    assert got["weekly"]["new_high"] is None


def test_short_holiday_week_is_completed_on_thursday():
    stock, bench = _source(end=date(2026, 4, 2), n=330)
    got = observe_rs_highs(stock, bench, as_of=date(2026, 4, 2))
    assert got["weekly"]["as_of"] == "2026-04-02"
    assert got["weekly"]["new_high"] is True


def test_midweek_source_does_not_fake_weekly_completion():
    stock, bench = _source()
    got = observe_rs_highs(stock, bench, as_of=date(2026, 10, 7))
    assert got["daily"]["as_of"] == "2026-10-07"
    assert got["weekly"]["as_of"] == "2026-10-02"


def test_source_invalid_duplicate_day_fails_closed():
    stock, bench = _source()
    duplicate = pd.concat([stock, stock.iloc[[-1]]])
    got = observe_rs_highs(duplicate, bench, as_of=date(2026, 10, 9))
    assert got["daily"]["new_high"] is None
    assert got["weekly"]["new_high"] is None
    assert got["daily"]["reason"] == "invalid_daily_source_index"


def test_unavailable_when_short_history_or_non_session():
    stock, bench = _source(n=80)
    x = observe_rs_highs(stock, bench, as_of=date(2026, 10, 9))
    assert x["daily"]["new_high"] is None
    assert x["weekly"]["new_high"] is None
    assert observe_rs_highs(stock, bench, as_of=date(2026, 10, 10))["daily"]["reason"] == "not_nyse_session"


def test_roster_is_derived_not_ranked_and_preserves_unknown():
    from scripts.build_leader_radar import _build_rs_high_roster
    rows = [
        {"ticker": "Z", "state": "LEADERSHIP", "display_chips": {
            "rs_high_watch": {"daily": {"new_high": True, "rs_leads_price": True, "as_of": "2026-10-09"},
                              "weekly": {"new_high": None, "as_of": None}}}},
        {"ticker": "A", "state": "BREAKAWAY", "display_chips": {
            "rs_high_watch": {"daily": {"new_high": True, "rs_leads_price": False, "as_of": "2026-10-09"},
                              "weekly": {"new_high": True, "as_of": "2026-10-09"}}}},
    ]
    v = _build_rs_high_roster(rows, as_of="2026-10-09", stale=False)
    assert [x["ticker"] for x in v["daily"]] == ["A", "Z"]
    assert [x["ticker"] for x in v["weekly"]] == ["A"]
    assert v["unknown"]["weekly"] == 1
    assert v["clock_as_of"]["weekly"] == "2026-10-09"
    assert v["stale"] is False


def test_roster_not_promoted_when_payload_stale():
    from scripts.build_leader_radar import _build_rs_high_roster
    v = _build_rs_high_roster([], as_of="2026-10-09", stale=True)
    assert v["daily"] == v["weekly"] == []
    assert v["stale"] is True


def test_recent_daily_high_remains_visible_during_pullback():
    stock, bench = _source()
    ratio_before = float((stock / bench).iloc[-6])
    stock.iloc[-5:] = bench.iloc[-5:].to_numpy() * (ratio_before * 0.98)
    got = observe_rs_highs(stock, bench, as_of=date(2026, 10, 9))
    assert got["daily"]["new_high"] is False
    assert got["daily"]["recent"]["since_last_high"] == 5
    assert got["daily"]["recent"]["last_high_as_of"] == stock.index[-6].date().isoformat()
    assert got["daily"]["recent"]["high_prints_in_window"] > 0


def test_weekly_high_remains_visible_one_week_after_nonconfirmation():
    stock, bench = _source()
    prior = pd.Timestamp(date(2026, 10, 2))
    current = pd.Timestamp(date(2026, 10, 9))
    last_week_ratio = float(stock.loc[prior] / bench.loc[prior])
    stock.loc[current] = bench.loc[current] * last_week_ratio * 0.95
    got = observe_rs_highs(stock, bench, as_of=date(2026, 10, 9))
    assert got["weekly"]["new_high"] is False
    assert got["weekly"]["recent"]["last_high_as_of"] == "2026-10-02"
    assert got["weekly"]["recent"]["since_last_high"] == 1


def test_recent_watch_missing_old_session_is_unknown_not_silently_empty():
    stock, bench = _source()
    stock = stock.drop(stock.index[-264])
    got = observe_rs_highs(stock, bench, as_of=date(2026, 10, 9))
    assert got["daily"]["new_high"] is True
    assert got["daily"]["recent"]["high_prints_in_window"] is None
    assert got["daily"]["recent"]["reason"] == "source_gap_or_nonpositive_close"


def test_future_duplicate_session_cannot_alter_historical_highs():
    stock, bench = _source()
    cut = date(2026, 10, 7)
    original = observe_rs_highs(stock, bench, as_of=cut)
    future_duplicate = pd.concat([stock, stock.loc[["2026-10-09"]]])
    assert observe_rs_highs(future_duplicate, bench, as_of=cut) == original


def test_recent_roster_retains_name_after_high_print_is_over():
    from scripts.build_leader_radar import _build_rs_high_roster
    rows = [
        {"ticker": "STALK", "state": "QUIET_ACCUMULATION", "entry_read": {"key": "building"}, "display_chips": {
            "rs_high_watch": {
                "daily": {"new_high": False, "recent": {
                    "last_high_as_of": "2026-10-06", "since_last_high": 3,
                    "reason": None}},
                "weekly": {"new_high": False, "recent": {
                    "last_high_as_of": "2026-10-02", "since_last_high": 1,
                    "reason": None}},
            }
        }},
        {"ticker": "FRESH", "state": "BREAKAWAY", "entry_read": {"key": "in_motion"}, "display_chips": {
            "rs_high_watch": {
                "daily": {"new_high": True, "as_of": "2026-10-09"},
                "weekly": {"new_high": None, "as_of": None},
            }
        }},
        {"ticker": "GAP", "state": "NONE", "display_chips": {
            "rs_high_watch": {
                "daily": {"new_high": None, "recent": {"reason": "missing"}},
                "weekly": {"new_high": None, "recent": {"reason": "missing"}},
            }
        }},
    ]
    r = _build_rs_high_roster(rows, as_of="2026-10-09", stale=False)
    assert [x["ticker"] for x in r["recent"]] == ["STALK"]
    assert r["recent"][0]["sessions_since_daily"] == 3
    assert r["recent"][0]["entry_read_key"] == "building"
    assert [x["ticker"] for x in r["daily"]] == ["FRESH"]
    assert r["daily"][0]["entry_read_key"] == "in_motion"
    assert r["unknown"]["recent"] == 1
    assert all(x["ticker"] != "FRESH" for x in r["recent"])



def test_real_leader_radar_builder_publishes_rs_watch_and_html(tmp_path):
    """Owner pipeline: existing roster artifact and page consume this lens."""
    import json
    import os
    from pathlib import Path
    from unittest.mock import patch

    from jinja2 import Environment, FileSystemLoader

    from test_build_leader_radar import _build_fixture_root
    from scripts.build_leader_radar import build

    root = _build_fixture_root(tmp_path, ["AAPL", "MSFT"])
    with patch("lib.config.ROOT", root), \
         patch("lib.config.data_dir", lambda: root / "data"), \
         patch("lib.config.load", lambda: {
             "storage": {"data_dir": "data", "site_dir": "site"},
             "leader_radar": {"enabled": True, "basket_keys": ["mag7"], "dow30": []},
         }), patch.dict(os.environ, {"COLLECT_LANE": "express"}):
        artifact = build(data_root=root / "data", site_root=root / "site")

    assert artifact["rs_high_roster"]["authority"] == "display_only"
    assert artifact["rs_high_roster"]["population_rows"] == 2
    assert artifact["rs_high_roster"]["clock_as_of"]["daily"] == artifact["as_of"]
    assert artifact["rs_high_roster"]["clock_as_of"]["weekly"] is not None
    assert len(artifact["rows"]) == 2
    for row in artifact["rows"]:
        watch = row["display_chips"]["rs_high_watch"]
        assert watch["schema"] == "leader_rs_highs.v1"
        assert watch["daily"]["lookback_sessions"] == 252
        assert watch["weekly"]["lookback_completed_weeks"] == 52
        assert watch["daily"]["new_high"] is not None
        assert "recent" in watch["weekly"]

    disk = json.loads((root / "site/leaderradar/radar.json").read_text())
    assert disk["rs_high_roster"] == artifact["rs_high_roster"]
    repo_root = Path(__file__).resolve().parents[1]
    template = Environment(
        loader=FileSystemLoader(str(repo_root / "templates")), autoescape=False,
    ).get_template("leader_radar.html.j2")
    html = template.render(leader_radar=disk)
    assert "RS highs to watch" in html
    assert "Recent leaders" in html
    assert "Daily" in html and "Weekly" in html
