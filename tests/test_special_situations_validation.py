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


def test_regressions_are_enrolled_in_pull_request_code_ci():
    """A data-only job is invisible to the pull-request code plan."""
    from pathlib import Path
    import yaml

    manifest = Path(__file__).resolve().parents[1] / ".github/ci/legacy-jobs.yml"
    jobs = yaml.safe_load(manifest.read_text())["jobs"]
    suite = "tests/test_special_situations_validation.py"
    owners = [job for job in jobs.values()
              if any(suite in step.get("run", "") for step in job.get("steps", []))]
    assert len(owners) == 1
    assert owners[0]["gate"] == "code"
    assert suite in owners[0]["paths"]
    assert "scripts/validate_special_situations.py" in owners[0]["paths"]


def test_ci_job_scope_preserves_all_existing_commands():
    from pathlib import Path
    from scripts.run_ci_pack import load_legacy_jobs

    manifest = Path(__file__).resolve().parents[1] / ".github/ci/legacy-jobs.yml"
    # Reuse the real manifest validator rather than a second scope parser.
    jobs = load_legacy_jobs(manifest, gate="code")
    assert any(job.job_id == "unrun-dark-guards" for job in jobs)


# R30: comparison-bearing statistics must use exactly the same input rows.
def mixed_pair_prices():
    """Forty losing pairs; ten winners whose own prior controls are unavailable."""
    index = pd.bdate_range("2024-01-01", "2024-09-30")
    dates = pd.bdate_range("2024-04-01", periods=50)
    events, columns = [], {}
    for i, day in enumerate(dates):
        ticker = f"SYNTHETIC_{i}"
        value = pd.Series(100.0, index=index)
        entry = index.get_loc(day) + 1
        winner = i % 5 == 4
        result = 0.90 if winner else -0.01
        value.iloc[entry:entry + 6] = np.linspace(100.0, 100.0 * (1 + result), 6)
        value.iloc[entry + 6:] = 100.0 * (1 + result)
        if winner:
            value.loc[value.index < day] = np.nan
        columns[ticker] = value
        events.append({"tk": ticker, "d": day, "category": "Synthetic event"})
    return pd.DataFrame(events), pd.DataFrame(columns), pd.Series(100.0, index=index)


def isolated_report(monkeypatch, tmp_path, events, closes, benchmark):
    import json
    monkeypatch.setattr(subject, "_HORIZONS", [5])
    monkeypatch.setattr(subject, "_PLACEBO_LAG", 20)
    monkeypatch.setattr(subject, "event_panel", lambda: events)
    monkeypatch.setattr(subject, "_us_closes", lambda: closes)
    monkeypatch.setattr(subject, "_spy", lambda _closes: benchmark)
    monkeypatch.setattr(subject.config, "data_dir", lambda: tmp_path / "fixture-data")
    monkeypatch.setattr(subject, "__file__", str(tmp_path / "scripts" / "validator.py"))
    subject.main()
    return (json.loads((tmp_path / "fixture-data/special_situations/validation_gate.json").read_text()),
            (tmp_path / "reports/special-situation-validation.md").read_text())


def test_mixed_cohort_cannot_promote_unmatched_winners(monkeypatch, tmp_path):
    events, closes, benchmark = mixed_pair_prices()
    gate, _ = isolated_report(monkeypatch, tmp_path, events, closes, benchmark)
    assert gate["event"]["5"]["n"] == 50  # All observed outcomes remain descriptive.
    assert gate["event"]["5"]["mean_abn"] == pytest.approx(0.172)
    assert gate["placebo_pre_event"]["5"]["n"] == 40
    assert gate["scored"] is False  # The positive mean is entirely in unpaired rows.
    assert gate["lead_horizon"] is None


def test_report_publishes_paired_and_full_populations_separately(monkeypatch, tmp_path):
    events, closes, benchmark = mixed_pair_prices()
    gate, report = isolated_report(monkeypatch, tmp_path, events, closes, benchmark)
    assert gate["verdict_basis"] == "promotion_paired"
    paired = gate["promotion_paired"]["5"]
    assert paired["event"]["n"] == paired["control"]["n"] == 40
    assert paired["event"]["mean_abn"] == pytest.approx(-0.01)
    assert paired["control"]["mean_abn"] == pytest.approx(0.0)
    assert paired["event"]["n_requested"] == paired["control"]["n_requested"] == 50
    assert paired["event"]["n_withheld"] == paired["control"]["n_withheld"] == 10
    assert paired["coverage"] == {"n_requested": 50, "n_paired": 40,
                                   "event_only": 10, "control_only": 0, "neither": 0}
    assert "## Paired comparison used for verdict" in report
    assert "| 5d | 40 | 40 | -0.01 |" in report
    assert "| 5d | 50 | 0.172 | 40 | 0.0 |" in report
    assert "Full-population descriptives" in report
    assert "| 5d | 40 / 50 | 10 | 0 | 0 |" in report


def test_pairing_is_by_event_row_not_ticker_or_filtered_position(monkeypatch):
    # The same ticker on different dates is not the same event/control pair.
    events = pd.DataFrame({"tk": ["SYNTHETIC"] * 3,
                           "d": pd.to_datetime(["2024-04-01", "2024-05-01", "2024-06-03"])},
                          index=[7, 7, 9])
    values = {
        pd.Timestamp("2024-04-01"): (pd.Timestamp("2024-04-02"), 0.80),
        pd.Timestamp("2024-05-01") - pd.offsets.BDay(20): (pd.Timestamp("2024-04-04"), -0.70),
        pd.Timestamp("2024-06-03"): (pd.Timestamp("2024-06-04"), -0.02),
        pd.Timestamp("2024-06-03") - pd.offsets.BDay(20): (pd.Timestamp("2024-05-07"), 0.01),
    }
    monkeypatch.setattr(subject, "_HORIZONS", [5])
    monkeypatch.setattr(subject, "_fwd_abn", lambda c, s, t, d, h, **kw: values.get(d))
    paired = subject._paired_study(events, pd.DataFrame(), None, shift_bdays=20)[5]
    assert paired["event"]["n"] == paired["control"]["n"] == 1
    assert paired["coverage"] == {"n_requested": 3, "n_paired": 1,
                                   "event_only": 1, "control_only": 1, "neither": 0}


def test_paired_empty_keeps_zero_denominator_without_estimates(monkeypatch):
    monkeypatch.setattr(subject, "_HORIZONS", [5])
    paired = subject._paired_study(pd.DataFrame(columns=["tk", "d"]), pd.DataFrame(), None,
                                   shift_bdays=20)[5]
    assert paired["event"] == paired["control"] == {"n": 0, "n_requested": 0, "n_withheld": 0}
    assert paired["coverage"] == {"n_requested": 0, "n_paired": 0,
                                   "event_only": 0, "control_only": 0, "neither": 0}


def test_all_paired_statistics_match_existing_descriptives(monkeypatch):
    events, closes, benchmark = mixed_pair_prices()
    closes = closes.fillna(100.0)  # All original missing control legs are now available.
    monkeypatch.setattr(subject, "_HORIZONS", [5])
    event = subject._study(events, closes, benchmark)
    control = subject._study(events, closes, benchmark, shift_bdays=20)
    pair = subject._paired_study(events, closes, benchmark, shift_bdays=20)[5]
    assert pair["event"] == event[5]
    assert pair["control"] == control[5]
    assert pair["coverage"]["n_paired"] == 50
    assert subject._verdict({5: pair["event"]}, {5: pair["control"]}) == subject._verdict(event, control)
    assert subject._verdict(event, control) == (True, 5)


def test_positive_surviving_pairs_can_still_pass_with_missing_controls(monkeypatch, tmp_path):
    events, closes, benchmark = mixed_pair_prices()
    for i, row in enumerate(events.itertuples(index=False)):
        if i % 5 == 4:
            continue
        entry = closes.index.get_loc(row.d) + 1
        result = 0.03 + (i % 4) * 0.01
        closes.iloc[entry:entry + 6, i] = np.linspace(100, 100 * (1 + result), 6)
        closes.iloc[entry + 6:, i] = 100 * (1 + result)
    gate, _ = isolated_report(monkeypatch, tmp_path, events, closes, benchmark)
    pair = gate["promotion_paired"]["5"]
    assert pair["event"]["n"] == 40
    assert pair["event"]["mean_abn"] > 0
    assert gate["scored"] is True  # Not a blanket refusal on any attrition.
    assert gate["lead_horizon"] == 5


def test_unpaired_outcome_magnitude_cannot_change_paired_statistics(monkeypatch):
    events, closes, benchmark = mixed_pair_prices()
    monkeypatch.setattr(subject, "_HORIZONS", [5])
    original = subject._paired_study(events, closes, benchmark, shift_bdays=20)
    for i, row in enumerate(events.itertuples(index=False)):
        if i % 5 == 4:
            entry = closes.index.get_loc(row.d) + 1
            closes.iloc[entry:entry + 6, i] = np.linspace(100, 10, 6)
            closes.iloc[entry + 6:, i] = 10
    assert subject._paired_study(events, closes, benchmark, shift_bdays=20) == original
    assert subject._study(events, closes, benchmark)[5]["mean_abn"] < 0


def test_pairing_preserves_results_under_reordering_and_duplicate_indexes(monkeypatch):
    events, closes, benchmark = mixed_pair_prices()
    monkeypatch.setattr(subject, "_HORIZONS", [3, 5])
    original = subject._paired_study(events, closes, benchmark, shift_bdays=20)
    shuffled = events.sample(frac=1, random_state=41)
    shuffled.index = [0] * len(shuffled)
    assert subject._paired_study(shuffled, closes, benchmark, shift_bdays=20) == original


def test_pair_membership_is_horizon_specific_and_sources_unchanged(monkeypatch):
    closes, benchmark = prices()
    events = pd.DataFrame({"tk": ["SYNTHETIC"], "d": [pd.Timestamp("2024-01-15")]})
    before = (events.copy(deep=True), closes.copy(deep=True), benchmark.copy(deep=True))
    monkeypatch.setattr(subject, "_HORIZONS", [3, 5])
    paired = subject._paired_study(events, closes, benchmark, shift_bdays=5)
    assert paired[3]["coverage"]["n_paired"] == 1
    assert paired[5]["coverage"]["n_paired"] == 0
    assert paired[5]["coverage"]["event_only"] == 1
    pd.testing.assert_frame_equal(events, before[0])
    pd.testing.assert_frame_equal(closes, before[1])
    pd.testing.assert_series_equal(benchmark, before[2])


def test_equal_counts_from_disjoint_rows_are_not_pairs(monkeypatch):
    events = pd.DataFrame({"tk": ["SYNTHETIC", "SYNTHETIC"],
                           "d": pd.to_datetime(["2024-04-01", "2024-05-01"])})
    monkeypatch.setattr(subject, "_HORIZONS", [5])
    def selected(c, s, t, d, h, **kw):
        available = d == events.iloc[0].d or d == events.iloc[1].d - pd.offsets.BDay(20)
        return (d + pd.offsets.BDay(), 0.1) if available else None
    monkeypatch.setattr(subject, "_fwd_abn", selected)
    pair = subject._paired_study(events, pd.DataFrame(), None, shift_bdays=20)[5]
    assert pair["event"]["n"] == pair["control"]["n"] == 0
    assert pair["coverage"] == {"n_requested": 2, "n_paired": 0,
                                "event_only": 1, "control_only": 1, "neither": 0}


@pytest.mark.parametrize("lag", [0, -1])
def test_paired_study_rejects_nonprior_controls(monkeypatch, lag):
    monkeypatch.setattr(subject, "_HORIZONS", [5])
    with pytest.raises(ValueError, match="positive pre-event shift"):
        subject._paired_study(pd.DataFrame(columns=["tk", "d"]), pd.DataFrame(), None,
                              shift_bdays=lag)


# The control's registered lead time cannot move to a later available price.
def anchored_control_prices(*, missing=(), holidays=()):
    index = pd.bdate_range("2024-08-01", "2024-12-20")
    index = index.difference(pd.to_datetime(list(holidays)))
    closes = pd.DataFrame({"SYNTHETIC": 100.0 + np.arange(len(index))}, index=index)
    closes.loc[closes.index.isin(pd.to_datetime(list(missing))), "SYNTHETIC"] = np.nan
    return closes, pd.Series(100.0, index=index)


def test_anchored_control_does_not_move_41_sessions_toward_event(monkeypatch):
    focal = pd.Timestamp("2024-12-02")
    closes, benchmark = anchored_control_prices()
    closes.loc[closes.index < "2024-11-01", "SYNTHETIC"] = np.nan
    events = pd.DataFrame({"tk": ["SYNTHETIC"], "d": [focal]})
    monkeypatch.setattr(subject, "_HORIZONS", [5])
    # The first available security window ends Nov 8, before the Dec 2 filing,
    # but its Nov 1 entry is 41 benchmark sessions after the intended Sep 5.
    assert subject._fwd_abn(closes, benchmark, "SYNTHETIC", focal, 5) is not None
    control = subject._study(events, closes, benchmark, shift_bdays=63)[5]
    paired = subject._paired_study(events, closes, benchmark, shift_bdays=63)[5]
    assert control == {"n": 0, "n_requested": 1, "n_withheld": 1}
    assert paired["coverage"] == {"n_requested": 1, "n_paired": 0,
                                   "event_only": 1, "control_only": 0, "neither": 0}


def test_anchored_control_missing_first_session_is_withheld():
    closes, benchmark = anchored_control_prices(missing=("2024-09-05",))
    result = subject._fwd_abn(closes, benchmark, "SYNTHETIC",
                              pd.Timestamp("2024-09-04"), 5,
                              end_before=pd.Timestamp("2024-12-02"))
    assert result is None


def test_anchored_control_respects_observed_calendar_holiday():
    closes, benchmark = anchored_control_prices(holidays=("2024-09-05",))
    result = subject._fwd_abn(closes, benchmark, "SYNTHETIC",
                              pd.Timestamp("2024-09-04"), 5,
                              end_before=pd.Timestamp("2024-12-02"))
    assert result is not None
    assert result[0] == pd.Timestamp("2024-09-06")
    expected = closes.loc["2024-09-13", "SYNTHETIC"] / closes.loc["2024-09-06", "SYNTHETIC"] - 1
    assert result[1] == pytest.approx(expected)


def test_anchored_control_rejection_does_not_inspect_outcome_returns():
    closes, benchmark = anchored_control_prices(missing=("2024-09-05",))
    reads = []
    class TracedOutcomes(pd.Series):
        def asof(self, *args, **kwargs):
            reads.append(args)
            return super().asof(*args, **kwargs)
    result = subject._fwd_abn(closes, TracedOutcomes(benchmark), "SYNTHETIC",
                              pd.Timestamp("2024-09-04"), 5,
                              end_before=pd.Timestamp("2024-12-02"))
    assert result is None
    assert reads == []


def test_anchored_control_does_not_change_post_event_entry_convention():
    closes, benchmark = anchored_control_prices(missing=("2024-12-03",))
    result = subject._fwd_abn(closes, benchmark, "SYNTHETIC",
                              pd.Timestamp("2024-12-02"), 5)
    assert result is not None
    assert result[0] == pd.Timestamp("2024-12-04")
