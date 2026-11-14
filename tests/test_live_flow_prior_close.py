"""Tests for lib.live_flow_prior_close.select_prior_close (pure selector).

Hand-built frames only — no provider, no IO, no git.  The session/holiday
truths below are fixed NYSE dates from the calendar's published rules
(2026-10-15/16/19 are Thu/Fri/Mon sessions; 2026-01-19 is MLK Day; 2026-12-25
is Christmas).  Every malformed case must land on the single "unknown" path
(``None``), never a raise.
"""

from __future__ import annotations

import pandas as pd
import pytest

from lib.live_flow_prior_close import select_prior_close

MON = "2026-10-19"   # Monday session
TUE = "2026-10-20"   # Tuesday session
THU = "2026-10-15"   # Thursday session
FRI = "2026-10-16"   # Friday session
SAT = "2026-10-17"
SUN = "2026-10-18"


def frame(rows, column="close_price"):
    """Date-labelled single-column frame from (iso_date, value) rows."""
    index = pd.DatetimeIndex([pd.Timestamp(d) for d, _ in rows])
    return pd.DataFrame({column: [v for _, v in rows]}, index=index)


def test_monday_selects_prior_friday():
    assert select_prior_close(frame([(FRI, 100.0), (MON, 101.0)]), MON) == 100.0


def test_friday_selects_thursday():
    assert select_prior_close(frame([(THU, 50.5), (FRI, 51.0)]), FRI) == 50.5


def test_weekend_session_date_is_unknown():
    df = frame([(FRI, 100.0), (MON, 101.0)])
    assert select_prior_close(df, SAT) is None
    assert select_prior_close(df, SUN) is None


def test_holiday_session_date_is_unknown():
    df = frame([("2026-01-16", 90.0), ("2026-12-24", 70.0)])
    assert select_prior_close(df, "2026-01-19") is None    # MLK Day 2026 (Mon)
    assert select_prior_close(df, "2026-12-25") is None    # Christmas 2026 (Fri)


def test_session_after_monday_holiday_uses_prior_friday():
    # Prior calendar day of Tue 2026-01-20 is the MLK holiday -> Friday 01-16.
    df = frame([("2026-01-15", 88.0), ("2026-01-16", 90.0), ("2026-01-20", 91.0)])
    assert select_prior_close(df, "2026-01-20") == 90.0


def test_stale_store_returns_none():
    # Latest stored row predates the expected prior session (2026-10-15).
    df = frame([("2026-10-13", 49.0), ("2026-10-14", 49.5)])
    assert select_prior_close(df, FRI) is None


def test_missing_close_price_column_returns_none():
    df = frame([(THU, 50.5), (FRI, 51.0)], column="close")   # adjusted basis only
    assert select_prior_close(df, FRI) is None


def test_uses_close_price_not_dividend_adjusted_close():
    index = pd.DatetimeIndex([pd.Timestamp(THU), pd.Timestamp(FRI)])
    df = pd.DataFrame({"close": [48.0, 48.5],           # total-return basis
                       "close_price": [50.5, 51.0]},    # dividend-unadjusted
                      index=index)
    assert select_prior_close(df, FRI) == 50.5


def test_same_day_and_future_rows_alone_return_none():
    # The store holds only the session itself and later: expected 10-16 absent.
    df = frame([(MON, 101.0), (TUE, 102.0)])
    assert select_prior_close(df, MON) is None


def test_same_day_and_future_rows_do_not_disturb_expected_prior():
    df = frame([(THU, 50.5), (FRI, 51.0), (MON, 101.0), (TUE, 102.0)])
    assert select_prior_close(df, MON) == 51.0


def test_duplicate_expected_date_returns_none():
    df = frame([(THU, 50.5), (FRI, 51.0), (FRI, 51.25), (MON, 101.0)])
    assert select_prior_close(df, MON) is None


def test_unsorted_rows_match_expected_date_not_position():
    # Expected row (FRI) is neither first nor last; iloc[-1] is THU.
    df = frame([(MON, 101.0), (THU, 50.5), (FRI, 51.0)])
    assert select_prior_close(df, MON) == 51.0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"),
                                 0.0, -423.5])
def test_nonfinite_or_nonpositive_close_price_returns_none(bad):
    df = frame([(THU, 50.5), (FRI, bad)])
    assert select_prior_close(df, MON) is None


@pytest.mark.parametrize("bad", ["51.0", True, None])
def test_non_numeric_close_price_returns_none(bad):
    df = frame([(THU, 50.5), (FRI, bad)])
    assert select_prior_close(df, MON) is None


@pytest.mark.parametrize("bad", ["", "not-a-date", "2026-13-45", 20261019, None])
def test_invalid_session_date_returns_none(bad):
    df = frame([(FRI, 51.0), (MON, 101.0)])
    assert select_prior_close(df, bad) is None


def test_non_datetime_index_returns_none():
    df = pd.DataFrame({"close_price": [50.5, 51.0]})         # RangeIndex
    assert select_prior_close(df, MON) is None


def test_timezone_aware_index_returns_none():
    index = pd.DatetimeIndex([pd.Timestamp(THU), pd.Timestamp(FRI)],
                             tz="America/New_York")
    df = pd.DataFrame({"close_price": [50.5, 51.0]}, index=index)
    assert select_prior_close(df, MON) is None


def test_none_or_empty_frame_returns_none():
    assert select_prior_close(None, MON) is None
    assert select_prior_close(frame([]), MON) is None

@pytest.mark.parametrize("raw", ["20261019", "2026-W43-1"])
def test_session_uses_canonical_calendar_date(raw):
    assert select_prior_close(frame([(FRI, 500)]), raw) is None


def test_intraday_timestamp_is_not_a_daily_close_label():
    assert select_prior_close(frame([("2026-10-16T15:30:00", 500)]), MON) is None


def test_nat_index_is_malformed_even_with_a_prior_session():
    df = pd.DataFrame({"close_price": [500, 600]}, index=pd.DatetimeIndex([FRI, pd.NaT]))
    assert select_prior_close(df, MON) is None


def test_earliest_calendar_date_stays_unknown():
    assert select_prior_close(frame([(FRI, 500)]), "0001-01-01") is None
