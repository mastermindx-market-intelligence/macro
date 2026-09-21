"""PENDING: 15 failing acceptance cases for the platform-blocked clock repair.
Not implemented, not release-qualified, and not part of the passing suite.
Run explicitly with pytest after the exact source-edit gate is resolved.
"""
import pytest
import pandas as pd
import numpy as np
from tests.test_china_participation import _price_context_fixture, _price_context, _board_fixture


# Independent build-time clock: equal old source dates must not certify freshness.
def _timed_context(monkeypatch, *, now=None, asof="2026-09-18", change=None):
    from datetime import datetime, timezone
    from engine import china_participation as pc
    from lib import store
    prices, bench, _ = _price_context_fixture()
    inputs = {("china_search", "closes"): prices,
              ("china", "510300.SS"): bench.to_frame("close"),
              ("china_board_breadth", "breadth"): _board_fixture(),
              ("china", "ETF"): prices.iloc[:, 0].to_frame("close")}
    if change:
        change(inputs)
    monkeypatch.setattr(store, "read", lambda g, n: inputs.get((g, n)))
    return pc.load_breadth_context(asof=asof, sector_universe={"ETF": ["Banks"]},
        now=now if now is not None else datetime(2026, 9, 18, 10, tzinfo=timezone.utc))


def test_timing_identically_old_inputs_are_delayed_not_current(monkeypatch):
    from datetime import datetime, timezone
    r = _timed_context(monkeypatch, now=datetime(2026, 9, 21, 12, tzinfo=timezone.utc))
    assert r["timing"]["expected_session"] == "2026-09-21"
    assert r["timing"]["status"] == "delayed"
    assert r["sample"]["status"] == r["daily_board"]["status"] == "delayed"
    assert r["sample"]["asof"] == "2026-09-18"
    assert r["sample"]["current_comparison"] is None
    assert r["sectors"]["eligible"] == 0
    assert r["timing"]["sources"]["sample"]["sessions_behind"] == 1


@pytest.mark.parametrize("instant,expected,state", [
    ("2026-09-18T09:00:00+00:00", "2026-09-18", "current"),
    ("2026-09-20T12:00:00+00:00", "2026-09-18", "current"),
    ("2026-09-21T08:59:00+00:00", "2026-09-18", "current"),
    ("2026-09-21T09:00:00+00:00", "2026-09-21", "delayed"),
    ("2026-09-25T12:00:00+00:00", "2026-09-24", "delayed"),
])
def test_timing_uses_existing_settle_weekend_and_holiday_rules(monkeypatch, instant, expected, state):
    from datetime import datetime
    r = _timed_context(monkeypatch, now=datetime.fromisoformat(instant))
    assert r["timing"]["expected_session"] == expected
    assert r["timing"]["status"] == state
    assert r["timing"]["calendar_basis"] == "lib.cn_calendar.conservative_rules"


def test_timing_unsettled_assessment_cannot_include_same_day_spike(monkeypatch):
    from datetime import datetime, timezone
    def future(inputs):
        for key in (("china_search", "closes"), ("china", "510300.SS"), ("china", "ETF")):
            inputs[key].loc[pd.Timestamp("2026-09-21")] = 9999.0
    r = _timed_context(monkeypatch, asof="2026-09-21", change=future,
                       now=datetime(2026, 9, 21, 8, tzinfo=timezone.utc))
    assert r["assessment_asof"] == "2026-09-21"
    assert r["timing"]["calculation_asof"] == "2026-09-18"
    assert r["timing"]["status"] == "unsettled"
    assert r["sample"]["windows"]["20"]["median_return_pct"] == 0
    assert r["timing"]["sources"]["sample"]["observed_through"] == "2026-09-21"
    assert r["timing"]["sources"]["sample"]["after_cutoff_rows"] == 1
    assert r["sample"]["current_comparison"] is None


def test_timing_different_board_and_sample_dates_are_explicit(monkeypatch):
    def older_board(inputs):
        inputs[("china_board_breadth", "breadth")].index = pd.to_datetime(["2026-09-17"])
    r = _timed_context(monkeypatch, change=older_board)
    assert r["timing"]["status"] == "mixed"
    assert r["timing"]["sources"]["daily_board"]["used_asof"] == "2026-09-17"
    assert r["timing"]["sources"]["sample"]["used_asof"] == "2026-09-18"


def test_timing_fresh_row_with_bad_benchmark_has_no_valid_clock(monkeypatch):
    def bad_benchmark(inputs):
        inputs[("china", "510300.SS")].iloc[-1] = np.nan
    r = _timed_context(monkeypatch, change=bad_benchmark)
    b = r["timing"]["sources"]["benchmark"]
    assert b["frame_through"] == "2026-09-18"
    assert b["observed_through"] == "2026-09-17"
    assert b["status"] == "unavailable"
    assert r["timing"]["status"] == "partial"


def test_timing_fresh_but_undercovered_panel_remains_partial(monkeypatch):
    def thin(inputs):
        inputs[("china_search", "closes")].iloc[-1, 4:] = np.nan
    r = _timed_context(monkeypatch, change=thin)
    assert r["timing"]["status"] == "partial"
    assert r["timing"]["sources"]["sample"]["status"] == "insufficient_coverage"
    assert r["sample"]["quote_count"] == 4


def test_timing_calendar_failure_keeps_old_values_but_no_current_claim(monkeypatch):
    from lib import cn_calendar
    def unavailable(_now):
        raise ValueError("calendar unavailable")
    monkeypatch.setattr(cn_calendar, "expected_last_session", unavailable)
    r = _timed_context(monkeypatch)
    assert r["timing"]["status"] == "unavailable"
    assert r["timing"]["expected_session"] is None
    assert r["sample"]["current_comparison"] is None
    assert r["sample"]["status"] != "current"


@pytest.mark.parametrize("clock", ["not a clock", float("nan"), pd.NaT])
def test_timing_invalid_clock_never_defaults_to_fresh(monkeypatch, clock):
    r = _timed_context(monkeypatch, now=clock)
    assert r["timing"]["status"] == "unavailable"
    assert r["sample"]["current_comparison"] is None


def test_timing_current_measurements_match_prior_arithmetic(monkeypatch):
    import json
    prices, bench, names = _price_context_fixture()
    expected = _price_context(prices, bench, names)
    r = _timed_context(monkeypatch)
    assert r["timing"]["status"] == "current"
    assert r["sample"]["windows"] == expected["windows"]
    assert r["sample"]["trend"] == expected["trend"]
    json.dumps(r, allow_nan=False)
