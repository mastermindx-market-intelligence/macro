"""Research diagnostics must not mistake data coverage for demand or alpha."""
from pathlib import Path

import pandas as pd
import pytest

AUDITOR = Path(__file__).parents[1] / "research/intelligence_network/demand_audit.py"


def load_audit():
    assert AUDITOR.exists(), "The point-in-time demand auditor has not been built"
    from research.intelligence_network.demand_audit import audit_frame
    return audit_frame


def row(ticker="AAA", app="App", day="2026-09-17", count=2000,
        rating=4.5, seen=None, publisher="Publisher"):
    return {"Ticker": ticker, "App": app, "Publisher": publisher,
            "Time": day, "Count": count, "Rating": rating,
            "_first_seen": seen or day + "T12:00:00Z"}


def audit(rows, **kwargs):
    return load_audit()(pd.DataFrame(rows, columns=list(row())),
                        observed_by="2026-09-19T12:00:00Z", **kwargs)


def test_display_cap_is_not_the_analytical_universe():
    result = audit([row(ticker=f"T{i:02d}") for i in range(20)])
    assert result["legacy"]["eligible_ticker_keys"] == 20
    assert result["legacy"]["display_count"] == 15
    assert result["legacy"]["strong_hidden_by_cap"] == 5
    assert result["use"] == "internal_research_only"


def test_later_first_seen_is_not_available_at_the_feed_cutoff():
    frame = pd.DataFrame([row(), row(day="2026-09-18", count=9000,
                                  seen="2026-09-19T01:27:00Z")])
    result = load_audit()(frame, observed_by="2026-09-18T18:41:00Z")
    assert result["availability"]["excluded_after_cutoff"] == 1
    assert result["snapshot_dates"]["latest"] == "2026-09-17"


@pytest.mark.parametrize("seen", [None, "invalid", "2026-09-17",
                                  "2026-09-17T12:00:00"])
def test_unknown_or_naive_availability_never_backfills(seen):
    record = row()
    record["_first_seen"] = seen
    result = audit([record])
    assert result["availability"]["excluded_unknown_clock"] == 1
    assert result["state"] == "NO_AVAILABLE_OBSERVATIONS"


def test_missing_app_is_not_a_demand_collapse():
    result = audit([row(app="A"), row(app="B"),
                    row(app="A", day="2026-09-18", count=2010)])
    assert result["comparisons"] == {"COHORT_CHANGED": 1}


def test_counter_reset_is_not_negative_demand():
    result = audit([row(), row(day="2026-09-18", count=20)])
    assert result["comparisons"] == {"COUNTER_DECREASE": 1}


@pytest.mark.parametrize("count,state", [(2100, "COMPARABLE_INCREASE"),
                                         (2000, "COMPARABLE_UNCHANGED")])
def test_only_matched_app_sets_can_be_compared(count, state):
    result = audit([row(), row(day="2026-09-18", count=count)])
    assert result["comparisons"] == {state: 1}


def test_new_and_missing_issuers_are_not_zero_growth():
    result = audit([row(ticker="OLD"), row(ticker="NEW", day="2026-09-18")])
    assert result["comparisons"] == {"CURRENT_ONLY": 1, "PRIOR_ONLY": 1}


def test_conflicting_versions_are_quarantined_not_arbitrarily_chosen():
    result = audit([row(), row(count=9000), row(day="2026-09-18")])
    assert result["quality"]["conflicting_snapshot_keys"] == 1
    assert result["comparisons"] == {"INVALID_OR_CONFLICTING_INPUT": 1}


def test_identical_duplicates_do_not_inflate_cohort_measurement():
    result = audit([row(), row(), row(day="2026-09-18", count=2010)])
    assert result["quality"]["duplicate_rows"] == 1
    assert result["comparisons"] == {"COMPARABLE_INCREASE": 1}


@pytest.mark.parametrize("count", [-1, float("inf"), "unknown", 2.5])
def test_invalid_counts_do_not_create_growth(count):
    result = audit([row(), row(day="2026-09-18", count=count)])
    assert result["quality"]["invalid_measurement_rows"] == 1
    assert result["comparisons"] == {"INVALID_OR_CONFLICTING_INPUT": 1}


def test_empty_is_not_a_successful_zero_observation():
    assert audit([])["state"] == "NO_AVAILABLE_OBSERVATIONS"


def test_cutoff_and_limit_are_explicit_and_validated():
    with pytest.raises(ValueError, match="timezone"):
        load_audit()(pd.DataFrame([row()]), observed_by="2026-09-19")
    with pytest.raises(ValueError, match="display_limit"):
        audit([row()], display_limit=0)


def test_aggregate_report_does_not_export_names_or_raw_provider_rows():
    result = audit([row(ticker="PRIVATE", app="Private Product")])
    assert "PRIVATE" not in str(result)
    assert "Private Product" not in str(result)


def test_future_snapshot_with_early_observation_is_still_excluded():
    result = audit([row(day="2026-09-25", seen="2026-09-17T12:00:00Z")])
    assert result["availability"]["excluded_bad_or_future_snapshot"] == 1
    assert result["state"] == "NO_AVAILABLE_OBSERVATIONS"


def test_missing_schema_is_not_silently_an_empty_feed():
    with pytest.raises(ValueError, match="Missing required columns"):
        load_audit()(pd.DataFrame(), observed_by="2026-09-19T12:00:00Z")


def test_input_is_unchanged_and_row_order_does_not_change_the_result():
    frame = pd.DataFrame([row(), row(day="2026-09-18", count=2100)])
    original = frame.copy(deep=True)
    fn = load_audit()
    a = fn(frame, observed_by="2026-09-19T12:00:00Z")
    b = fn(frame.iloc[::-1], observed_by="2026-09-19T12:00:00Z")
    assert a == b
    pd.testing.assert_frame_equal(frame, original)


def test_one_app_decrease_cannot_be_hidden_by_another_app_increase():
    result = audit([row(app="A"), row(app="B"),
        row(app="A", day="2026-09-18", count=1000),
        row(app="B", day="2026-09-18", count=9000)])
    assert result["comparisons"] == {"COUNTER_DECREASE": 1}
