"""Regression proofs for COT clocks; no network and no production data writes."""
import numpy as np
import pandas as pd
import pytest

from lib.cot_publication import (
    available_at, align_released, legacy_series, reconstruction_bound,
    released_series, scheduled_release, utc_timestamp,
)


@pytest.mark.parametrize("bad", [None, pd.NaT, "", "bad", "2026-10-09", 42, [], {}, [1, 2]])
def test_invalid_or_unzoned_instant_is_unknown(bad):
    assert pd.isna(utc_timestamp(bad))


def test_timezone_conversion_and_normal_release():
    assert utc_timestamp("2026-10-09T15:30:00-04:00") == pd.Timestamp("2026-10-09T19:30:00Z")
    assert scheduled_release("2026-10-06") == pd.Timestamp("2026-10-09T19:30:00Z")
    assert scheduled_release("2026-01-13") == pd.Timestamp("2026-01-16T20:30:00Z")


def test_monday_observation_is_not_shifted_to_thursday():
    assert scheduled_release("2025-11-10") == pd.Timestamp("2025-11-14T20:30:00Z")


def test_holiday_schedule_is_still_only_estimate():
    # Christmas Friday: expected Monday; historical context waits to Tuesday.
    assert scheduled_release("2026-12-22") == pd.Timestamp("2026-12-28T20:30:00Z")
    assert reconstruction_bound("2026-12-22") == pd.Timestamp("2026-12-29T05:00:00Z")


@pytest.mark.parametrize("asof,day", [
    ("2025-09-30", "2025-11-20T05:00:00Z"),
    ("2025-11-10", "2025-12-11T05:00:00Z"),
    ("2025-12-02", "2025-12-18T05:00:00Z"),
    ("2023-01-31", "2023-02-25T05:00:00Z"),
    ("2023-03-14", "2023-03-22T04:00:00Z"),
])
def test_announced_dates_get_conservative_next_midnight(asof, day):
    assert reconstruction_bound(asof) == pd.Timestamp(day)


@pytest.mark.parametrize("asof", ["2013-10-08", "2019-01-08", None, pd.NaT, "garbage"])
def test_unresolved_disruption_and_bad_dates_fail_closed(asof):
    assert pd.isna(reconstruction_bound(asof))


def test_expected_release_is_not_observed_vintage():
    assert pd.isna(available_at({"scheduled_release_at": "2026-10-09T19:30:00Z"}, report_date="2026-10-06"))
    assert pd.isna(available_at({"actual_release_at": "2026-10-09T19:30:00Z"}, report_date="2026-10-06"))


def test_observed_vintage_changes_only_after_retrieval():
    frame = pd.DataFrame({"net_spec_pct_oi": [20.0], "first_observed_at": ["2026-10-09T19:32:00Z"]}, index=pd.to_datetime(["2026-10-06"]))
    s = released_series(frame)
    points = pd.to_datetime(["2026-10-09T19:29:00Z", "2026-10-09T19:31:00Z", "2026-10-09T19:32:00Z"])
    out = align_released(s, points)
    assert out.iloc[:2].isna().all()
    assert out.iloc[2] == 20
    assert s.attrs["original_vintage_certified"] is False


def test_correction_never_reuses_first_observed_time():
    row = {"first_observed_at": "2026-10-09T19:32:00Z", "revised_at": "2026-10-12T11:00:00Z"}
    assert available_at(row, report_date="2026-10-06") == pd.Timestamp("2026-10-12T11:00:00Z")
    assert available_at(row, report_date="2026-10-06", mode="reconstructed") == pd.Timestamp("2026-10-12T11:00:00Z")


def test_version_clock_overrides_older_first_observation():
    row = {"first_observed_at": "2026-10-09T19:32:00Z", "version_observed_at": "2026-10-13T11:00:00Z"}
    assert available_at(row, report_date="2026-10-06") == pd.Timestamp("2026-10-13T11:00:00Z")


def test_future_observation_is_not_yet_a_valid_report():
    row = {"first_observed_at": "2026-10-01T12:00:00Z"}
    assert pd.isna(available_at(row, report_date="2026-10-06"))


def test_legacy_reconstruction_is_not_vintage_certification():
    frame = pd.DataFrame({"net_spec_pct_oi": [-5.0]}, index=pd.to_datetime(["2025-09-30"]))
    assert released_series(frame).empty
    s = legacy_series(frame)
    assert s.index[0] == pd.Timestamp("2025-11-20")
    out = align_released(s, pd.date_range("2025-10-01", "2025-11-21"))
    assert out.loc[:"2025-11-19"].isna().all()
    assert out.loc["2025-11-20"] == -5
    assert s.attrs["cot_availability_mode"] == "reconstructed"


def test_daily_rounding_never_turns_a_release_into_morning_knowledge():
    f = pd.DataFrame({"net_spec_pct_oi": [0.0], "first_observed_at": ["2026-10-09T19:32:00Z"]}, index=pd.to_datetime(["2026-10-06"]))
    s = released_series(f, daily=True)
    assert s.index[0] == pd.Timestamp("2026-10-10")
    out = align_released(s, pd.bdate_range("2026-10-09", "2026-10-13"))
    assert np.isnan(out.iloc[0])
    assert out.iloc[1] == 0.0  # Monday retains Saturday publication.


def test_wall_clock_staleness_and_explicit_missing_barrier():
    s = pd.Series([1.0, np.nan, 0.0], index=pd.to_datetime(["2026-10-03", "2026-10-10", "2026-10-17"]))
    out = align_released(s, pd.date_range("2026-10-02", "2026-11-01"), max_age_days=12)
    assert np.isnan(out.iloc[0])
    assert out.loc["2026-10-09"] == 1.0
    assert out.loc["2026-10-10":"2026-10-16"].isna().all()
    assert out.loc["2026-10-29"] == 0.0
    assert np.isnan(out.loc["2026-10-30"])


def test_multiple_same_release_reports_select_latest_observation():
    f = pd.DataFrame({"net_spec_pct_oi": [2.0, 1.0], "first_observed_at": ["2026-10-10T12:00:00Z"] * 2}, index=pd.to_datetime(["2026-10-06", "2026-09-29"]))
    assert released_series(f).tolist() == [2.0]


def test_late_correction_of_old_report_does_not_replace_current_report():
    f = pd.DataFrame({"net_spec_pct_oi": [1.0, 2.0], "version_observed_at": ["2026-10-13T12:00:00Z", "2026-10-09T19:32:00Z"]}, index=pd.to_datetime(["2026-09-29", "2026-10-06"]))
    out = align_released(released_series(f), pd.to_datetime(["2026-10-14T12:00:00Z"]))
    assert out.iloc[0] == 2.0


def test_mismatched_timezone_awareness_is_rejected():
    s = pd.Series([1.0], index=pd.to_datetime(["2026-10-09T19:30:00Z"]))
    with pytest.raises(ValueError):
        align_released(s, pd.to_datetime(["2026-10-12"]))


def test_invalid_mode_and_negative_age_rejected():
    with pytest.raises(ValueError):
        available_at({}, report_date="2026-10-06", mode="guess")
    with pytest.raises(ValueError):
        align_released(pd.Series([1], index=pd.to_datetime(["2026-10-01"])), pd.to_datetime(["2026-10-02"]), max_age_days=-1)
