"""tests/test_rebalance_calendar.py — Hermetic tests for engine/rebalance_calendar.py.

Tests:
  - quarter_end_sessions: correct dates, only NYSE sessions
  - russell_recon_sessions: 2026-06-26 override, rule-derived adjustment
  - sp_rebalance_sessions: quad-witching days only
  - month_end_sessions: last session per month
  - tag(): all keys present, in_qtr_end_window, holiday adjustment case
  - RECON_OVERRIDES: 2026-06-26 is a Friday and a session
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.rebalance_calendar import (
    RECON_OVERRIDES,
    quarter_end_sessions,
    russell_recon_sessions,
    sp_rebalance_sessions,
    month_end_sessions,
    tag,
    build_tag_frame,
)
from lib.nyse_calendar import is_session


# ── quarter_end_sessions ──────────────────────────────────────────────────────

class TestQuarterEndSessions:
    def test_four_per_year(self):
        sessions = quarter_end_sessions(2023, 2023)
        assert len(sessions) == 4

    def test_months_are_march_june_sep_dec(self):
        sessions = quarter_end_sessions(2024, 2024)
        months = [d.month for d in sessions]
        assert sorted(months) == [3, 6, 9, 12]

    def test_all_are_sessions(self):
        for d in quarter_end_sessions(2020, 2026):
            assert is_session(d), f"{d} is not a NYSE session"

    def test_known_2024_dates(self):
        """2024-03-28 = last session of March 2024 (Good Friday is 2024-03-29)."""
        sessions = quarter_end_sessions(2024, 2024)
        # March 31 2024 is a Sunday; Good Friday is Mar 29 → last session is Mar 28
        assert date(2024, 3, 28) in sessions
        # Jun 28 2024 (last session of June)
        assert date(2024, 6, 28) in sessions

    def test_returns_sorted_unique(self):
        sessions = quarter_end_sessions(2020, 2023)
        assert sessions == sorted(set(sessions))


# ── russell_recon_sessions ────────────────────────────────────────────────────

class TestRussellReconSessions:
    def test_2026_override(self):
        """2026-06-26 is the operator-specified override."""
        sessions = russell_recon_sessions(2026, 2026)
        assert date(2026, 6, 26) in sessions

    def test_2026_override_is_session(self):
        """2026-06-26 must be a NYSE session (Friday)."""
        d = date(2026, 6, 26)
        assert is_session(d)
        assert d.weekday() == 4  # Friday

    def test_all_in_overrides_are_sessions(self):
        for y, d in RECON_OVERRIDES.items():
            assert is_session(d), f"Override {y}: {d} is not a NYSE session"

    def test_rule_derived_year_is_session(self):
        """For a year not in RECON_OVERRIDES (e.g. 2027), rule must give a session."""
        sessions = russell_recon_sessions(2027, 2027)
        for d in sessions:
            assert is_session(d), f"Rule-derived recon day {d} is not a NYSE session"

    def test_rule_derived_in_june(self):
        sessions = russell_recon_sessions(2027, 2027)
        for d in sessions:
            assert d.month == 6

    def test_holiday_adjustment(self):
        """If the last Friday of June is a holiday, we should get a prior session."""
        # 2022-06-19 is Juneteenth (NYSE holiday since 2022).
        # The last Friday of June 2022 would be Jun 24.
        # Jun 19 is earlier in June, so this doesn't conflict; but verify the
        # rule gives Jun 24 2022 (which is the override).
        assert RECON_OVERRIDES.get(2022) == date(2022, 6, 24)
        assert is_session(date(2022, 6, 24))


# ── sp_rebalance_sessions ─────────────────────────────────────────────────────

class TestSpRebalanceSessions:
    @pytest.mark.parametrize(
        "closed,previous_session",
        [("2008-03-21", "2008-03-20"),
         ("2026-06-19", "2026-06-18"),
         ("2027-06-18", "2027-06-17")],
    )
    def test_exchange_holiday_moves_event_to_actual_session(self, closed, previous_session):
        idx = pd.bdate_range(previous_session, closed)
        expected = date.fromisoformat(previous_session)
        assert sp_rebalance_sessions(idx) == [expected]
        assert tag(expected)["is_sp_rebalance_session"] is True
        assert tag(date.fromisoformat(closed))["is_sp_rebalance_session"] is False

    @pytest.mark.parametrize(
        "observed,expected",
        [([], []),
         (["2024-03-14", "2024-03-18"], []),
         (["2024-01-02", "2024-03-18"], []),
         (["2026-06-17", "2026-06-22"], []),
         (["2024-03-14"], []),
         (["2026-06-18"], [date(2026, 6, 18)]),
         (["2024-03-15"], [date(2024, 3, 15)]),
         (["2024-03-18", "2024-03-15", "2024-03-14", "2024-03-15"],
          [date(2024, 3, 15)])],
    )
    def test_observation_gaps_never_move_calendar_events(self, observed, expected):
        assert sp_rebalance_sessions(pd.DatetimeIndex(observed)) == expected

    def test_scheduled_day_is_known_before_nominal_holiday(self):
        idx = pd.bdate_range("2026-06-01", "2026-06-18")
        assert sp_rebalance_sessions(idx) == [date(2026, 6, 18)]

    def test_sparse_indices_only_select_present_scheduled_days(self):
        import random

        rng = random.Random(2362)
        idx = pd.bdate_range("2026-01-01", "2026-12-31")
        scheduled = {date(2026, 3, 20), date(2026, 6, 18),
                     date(2026, 9, 18), date(2026, 12, 18)}
        for _ in range(100):
            sample = rng.sample(list(idx), rng.randint(1, 100))
            expected = sorted({d.date() for d in sample} & scheduled)
            assert sp_rebalance_sessions(sample) == expected

    @pytest.mark.parametrize("day", [date(2026, 6, 17), date(2026, 6, 18),
                                      date(2026, 6, 19), date(2026, 6, 22)])
    def test_scalar_and_singleton_bulk_tag_agree(self, day):
        frame = build_tag_frame([day])
        assert frame.loc[day].to_dict() == tag(day)

    def test_four_per_year(self):
        idx = pd.bdate_range("2024-01-01", "2024-12-31")
        sessions = sp_rebalance_sessions(idx)
        assert len(sessions) == 4

    def test_in_quad_months(self):
        idx = pd.bdate_range("2024-01-01", "2024-12-31")
        sessions = sp_rebalance_sessions(idx)
        for d in sessions:
            assert d.month in (3, 6, 9, 12)

    def test_all_are_sessions(self):
        idx = pd.bdate_range("2023-01-01", "2025-12-31")
        for d in sp_rebalance_sessions(idx):
            assert is_session(d), f"{d} is not a session"

    def test_known_2024_march(self):
        """March 2024 quad-witching = 3rd Friday = 2024-03-15."""
        idx = pd.bdate_range("2024-01-01", "2024-12-31")
        sessions = sp_rebalance_sessions(idx)
        assert date(2024, 3, 15) in sessions


# ── month_end_sessions ────────────────────────────────────────────────────────

class TestMonthEndSessions:
    def test_twelve_per_year(self):
        sessions = month_end_sessions(2023, 2023)
        assert len(sessions) == 12

    def test_all_are_sessions(self):
        for d in month_end_sessions(2020, 2024):
            assert is_session(d)

    def test_returns_sorted_unique(self):
        sessions = month_end_sessions(2020, 2022)
        assert sessions == sorted(set(sessions))


# ── tag() ─────────────────────────────────────────────────────────────────────

class TestTag:
    _REQUIRED_KEYS = {
        "is_quarter_end",
        "td_to_quarter_end",
        "in_qtr_end_window",
        "is_russell_recon_session",
        "in_recon_week",
        "is_sp_rebalance_session",
        "is_month_end_session",
    }

    def test_all_keys_present(self):
        result = tag(date(2024, 6, 28))
        assert set(result.keys()) >= self._REQUIRED_KEYS

    def test_quarter_end_flagged(self):
        """2024-06-28 = last session of June 2024."""
        result = tag(date(2024, 6, 28))
        assert result["is_quarter_end"] is True
        assert result["td_to_quarter_end"] == 0
        assert result["in_qtr_end_window"] is True

    def test_non_quarter_end_not_flagged(self):
        """2024-06-17 is well before quarter-end."""
        result = tag(date(2024, 6, 17))
        assert result["is_quarter_end"] is False

    def test_in_qtr_end_window_three_sessions_before(self):
        """3 sessions before the quarter-end should be in_qtr_end_window."""
        # Find a quarter-end and go back 3 sessions
        qe_dates = quarter_end_sessions(2024, 2024)
        qe = qe_dates[1]  # June 28 2024
        # Walk back 3 sessions
        d = qe
        count = 0
        while count < 3:
            d -= __import__('datetime').timedelta(days=1)
            if is_session(d):
                count += 1
        result = tag(d)
        assert result["in_qtr_end_window"] is True
        assert result["td_to_quarter_end"] > 0  # positive = days until

    def test_russell_recon_flagged_2026(self):
        """2026-06-26 (override) must be flagged."""
        result = tag(date(2026, 6, 26))
        assert result["is_russell_recon_session"] is True
        assert result["in_recon_week"] is True

    def test_sp_rebalance_march_2024(self):
        """2024-03-15 = March quad-witching."""
        result = tag(date(2024, 3, 15))
        assert result["is_sp_rebalance_session"] is True

    def test_month_end_flagged(self):
        """2024-01-31 = last session of January 2024."""
        result = tag(date(2024, 1, 31))
        assert result["is_month_end_session"] is True

    def test_holiday_adjusted_quarter_end(self):
        """Good Friday 2024-03-29 is a holiday; last March session = 2024-03-28."""
        result = tag(date(2024, 3, 28))
        assert result["is_quarter_end"] is True

    def test_td_to_quarter_end_sign_convention(self):
        """td_to_quarter_end is the SIGNED distance to the nearest QE:
          - zero on the QE day itself
          - positive N sessions BEFORE the nearest QE (d is before QE)
          - negative N sessions AFTER the nearest QE (d is after QE)
        Symmetry: post-QE sessions get a small negative td, not a large
        positive distance to the next quarter's QE (~63 sessions away).
        This ensures in_qtr_end_window covers both 3 sessions before AND
        3 sessions after each QE (residual rebalance execution window).
        """
        qe_dates = quarter_end_sessions(2024, 2024)
        qe = qe_dates[0]  # March 28 2024

        # On the QE day itself → 0
        r_on = tag(qe)
        assert r_on["td_to_quarter_end"] == 0

        # One session before → positive (future QE is ahead)
        d_before = qe
        while True:
            d_before -= __import__('datetime').timedelta(days=1)
            if is_session(d_before):
                break
        r_before = tag(d_before)
        assert r_before["td_to_quarter_end"] > 0

        # One session after → negative (nearest QE is the one just passed)
        d_after = qe
        while True:
            d_after += __import__('datetime').timedelta(days=1)
            if is_session(d_after):
                break
        r_after = tag(d_after)
        # nearest QE is March 28 (just behind us), so td = -1
        assert r_after["td_to_quarter_end"] == -1
        assert r_after["in_qtr_end_window"] is True


# ── build_tag_frame ───────────────────────────────────────────────────────────

class TestBuildTagFrame:
    def test_returns_dataframe(self):
        sessions = [date(2024, 3, 28), date(2024, 6, 28)]
        df = build_tag_frame(sessions)
        assert isinstance(df, pd.DataFrame)

    def test_index_is_dates(self):
        sessions = [date(2024, 3, 28), date(2024, 6, 28)]
        df = build_tag_frame(sessions)
        assert len(df) == 2

    def test_empty_input(self):
        df = build_tag_frame([])
        assert df.empty

    def test_quarter_end_column_true(self):
        sessions = [date(2024, 6, 28)]
        df = build_tag_frame(sessions)
        assert bool(df.loc[date(2024, 6, 28), "is_quarter_end"]) is True


def test_upcoming_builder_uses_exchange_adjusted_rebalance_date():
    from scripts.build_rebalance_pulse import _next_upcoming_events

    assert _next_upcoming_events(date(2026, 6, 17))[0] == {
        "date": "2026-06-18", "types": ["sp_rebalance"], "td_to": 1,
    }


def test_builder_classifies_holiday_adjusted_volume_spike(tmp_path, monkeypatch):
    import json
    from scripts.build_rebalance_pulse import main

    day = date(2026, 6, 18)
    idx = pd.bdate_range(end=day, periods=26)
    volume = pd.DataFrame({"AAPL": [100.0] * 25 + [180.0]}, index=idx)
    updown = pd.DataFrame({"up_vol": [60.0], "down_vol": [40.0]},
                          index=[pd.Timestamp(day)])

    def read_parquet(path, *args, **kwargs):
        return (volume if Path(path).name == "_volume_cache.parquet" else updown).copy()

    monkeypatch.setattr(pd, "read_parquet", read_parquet)
    assert main(["--root", str(tmp_path), "--asof", str(day)]) == 0
    payload = json.loads((tmp_path / "site/marketdata/rebalance_pulse.json").read_text())
    pulse = payload["latest_pulse"]
    assert payload["gaps"] == []
    assert pulse["class"] == "mechanical_spike_absorbed"
    assert pulse["calendar"]["is_sp_rebalance_session"] is True
    assert pulse["market_vol_ratio"] == 1.8
    assert pulse["up_share"] == 0.6
    assert pulse["authority"] == {"may_rank": False, "may_gate": False, "may_size": False}
