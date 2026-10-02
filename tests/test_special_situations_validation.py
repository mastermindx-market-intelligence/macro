"""Synthetic-calendar regressions: pre-event controls must really precede the event.

These import the production validator, but never fetch prices, classify filings,
write a live gate, or run the actual event panel. No empirical return claims.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import validate_special_situations as subject


def prices(*, missing=(), holidays=()):
    index = pd.bdate_range("2024-01-01", "2024-03-29")
    index = index.difference(pd.to_datetime(list(holidays)))
    series = pd.Series(100.0 + np.arange(len(index)), index=index)
    closes = pd.DataFrame({"SYNTHETIC": series})
    for day in missing:
        closes.loc[pd.Timestamp(day), "SYNTHETIC"] = np.nan
    return closes, pd.Series(100.0, index=index)


def study(monkeypatch, *, horizon, focal="2024-01-15", lag=5,
          missing=(), holidays=(), count=1):
    monkeypatch.setattr(subject, "_HORIZONS", [horizon])
    closes, benchmark = prices(missing=missing, holidays=holidays)
    events = pd.DataFrame({"tk": ["SYNTHETIC"] * count,
                           "d": [pd.Timestamp(focal)] * count})
    return subject._study(events, closes, benchmark, shift_bdays=lag)[horizon]


@pytest.mark.parametrize("horizon", [4, 5, 10])
def test_control_ending_on_or_after_focal_date_is_withheld(monkeypatch, horizon):
    # Lagged entry is Jan 9; horizon 4 ends Jan 15, exactly on the focal day.
    assert study(monkeypatch, horizon=horizon)["n"] == 0


def test_control_strictly_before_focal_date_is_kept(monkeypatch):
    assert study(monkeypatch, horizon=3)["n"] == 1


@pytest.mark.parametrize("focal", ["2024-01-13", "2024-01-14"])
def test_weekend_focal_boundary_does_not_admit_next_week(monkeypatch, focal):
    assert study(monkeypatch, horizon=5, focal=focal)["n"] == 0


def test_missing_security_session_cannot_extend_control_into_event(monkeypatch):
    # Missing Jan 12 pushes the third observed price from Jan 12 onto Jan 15.
    assert study(monkeypatch, horizon=3, missing=("2024-01-12",))["n"] == 0


def test_calendar_holiday_cannot_extend_control_into_event(monkeypatch):
    assert study(monkeypatch, horizon=3, holidays=("2024-01-12",))["n"] == 0


def test_event_study_still_measures_after_the_filing(monkeypatch):
    assert study(monkeypatch, horizon=5, lag=0)["n"] == 1


def test_focal_intraday_time_does_not_admit_same_date_close(monkeypatch):
    assert study(monkeypatch, horizon=4, focal="2024-01-15 16:30")["n"] == 0


def test_control_does_not_become_a_shorter_horizon(monkeypatch):
    assert study(monkeypatch, horizon=10)["n"] == 0
    assert study(monkeypatch, horizon=3)["n"] == 1


def test_withheld_rows_remain_in_requested_denominator(monkeypatch):
    result = study(monkeypatch, horizon=5, count=3)
    assert result["n"] == 0
    assert result["n_requested"] == 3
    assert result["n_withheld"] == 3


def test_unpriced_row_is_not_imputed_or_erased(monkeypatch):
    monkeypatch.setattr(subject, "_HORIZONS", [3])
    closes, benchmark = prices()
    events = pd.DataFrame({"tk": ["SYNTHETIC", "UNAVAILABLE"],
                           "d": [pd.Timestamp("2024-01-15")] * 2})
    result = subject._study(events, closes, benchmark, shift_bdays=5)[3]
    assert result["n"] == 1
    assert result["n_requested"] == 2
    assert result["n_withheld"] == 1


def test_empty_cohort_has_zero_coverage_not_an_invented_return(monkeypatch):
    monkeypatch.setattr(subject, "_HORIZONS", [3])
    closes, benchmark = prices()
    events = pd.DataFrame(columns=["tk", "d"])
    result = subject._study(events, closes, benchmark, shift_bdays=5)[3]
    assert result == {"n": 0, "n_requested": 0, "n_withheld": 0}


def test_valid_control_return_is_unchanged(monkeypatch):
    # Ten duplicate rows here test aggregation plumbing, not independence/power.
    result = study(monkeypatch, horizon=3, count=10)
    closes, benchmark = prices()
    original = subject._fwd_abn(closes, benchmark, "SYNTHETIC",
                                pd.Timestamp("2024-01-08"), 3)
    assert original is not None
    assert result["n"] == 10
    assert result["mean_abn"] == round(original[1], 4)
    assert result["n_requested"] == 10
    assert result["n_withheld"] == 0
    assert result["valid_hac"] is False


def test_all_rejected_controls_cannot_support_a_positive_verdict(monkeypatch):
    result = study(monkeypatch, horizon=5, count=40)
    event = {5: {"n": 40, "n_days": 40, "mean_abn": 0.20,
                 "valid_hac": True, "hac_t": 3.0}}
    assert subject._verdict(event, {5: result}) == (False, None)


def test_existing_post_event_return_convention_is_preserved():
    closes, benchmark = prices()
    result = subject._fwd_abn(closes, benchmark, "SYNTHETIC",
                              pd.Timestamp("2024-01-15"), 5)
    assert result is not None
    assert result[0] == pd.Timestamp("2024-01-16")
    expected = closes.loc["2024-01-23", "SYNTHETIC"] / closes.loc["2024-01-16", "SYNTHETIC"] - 1
    assert result[1] == pytest.approx(expected)


def test_source_frames_are_not_changed(monkeypatch):
    monkeypatch.setattr(subject, "_HORIZONS", [3, 5])
    closes, benchmark = prices()
    original_closes, original_benchmark = closes.copy(deep=True), benchmark.copy(deep=True)
    events = pd.DataFrame({"tk": ["SYNTHETIC"], "d": [pd.Timestamp("2024-01-15")]})
    subject._study(events, closes, benchmark, shift_bdays=5)
    pd.testing.assert_frame_equal(closes, original_closes)
    pd.testing.assert_series_equal(benchmark, original_benchmark)


def test_synthetic_report_exposes_control_coverage_and_boundary(monkeypatch, tmp_path):
    """Exercise the real JSON/report writer with only synthetic in-memory inputs.

    Both destinations are under pytest's temporary directory, never the actual
    event store, validation gate, report, or channel configuration.
    """
    import json

    monkeypatch.setattr(subject, "_HORIZONS", [3, 5])
    monkeypatch.setattr(subject, "_PLACEBO_LAG", 5)
    closes, benchmark = prices()
    events = pd.DataFrame({"tk": ["SYNTHETIC"], "d": [pd.Timestamp("2024-01-15")]})
    monkeypatch.setattr(subject, "event_panel", lambda: events)
    monkeypatch.setattr(subject, "_us_closes", lambda: closes)
    monkeypatch.setattr(subject, "_spy", lambda _closes: benchmark)
    monkeypatch.setattr(subject.config, "data_dir", lambda: tmp_path / "fixture-data")
    monkeypatch.setattr(subject, "__file__", str(tmp_path / "scripts" / "validator.py"))
    subject.main()
    gate = json.loads((tmp_path / "fixture-data/special_situations/validation_gate.json").read_text())
    report = (tmp_path / "reports/special-situation-validation.md").read_text()
    assert gate["schema"] == "special_situation.gate.v1"
    assert gate["scored"] is False
    assert gate["placebo_pre_event"]["3"]["n"] == 1
    assert gate["placebo_pre_event"]["5"]["n"] == 0
    assert "control exits strictly before focal filing day" in gate["method"]
    assert "## Window coverage" in report
    assert "| Horizon | Event kept / requested | Event withheld | Control kept / requested | Control withheld |" in report
    assert "| 3d | 1 / 1 | 0 | 1 / 1 | 0 |" in report
    assert "| 5d | 1 / 1 | 0 | 0 / 1 | 1 |" in report
    assert "not automatically news-free or independent" in report


def test_guard_rejects_before_reading_any_outcome_prices():
    closes, benchmark = prices()
    reads = []
    class TracedBenchmark(pd.Series):
        @property
        def _constructor(self):
            return TracedBenchmark
        def asof(self, *args, **kwargs):
            reads.append(args)
            return super().asof(*args, **kwargs)
    benchmark = TracedBenchmark(benchmark)
    result = subject._fwd_abn(closes, benchmark, "SYNTHETIC",
                              pd.Timestamp("2024-01-08"), 5,
                              end_before=pd.Timestamp("2024-01-15"))
    assert result is None
    assert reads == []
