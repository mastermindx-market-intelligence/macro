"""Synthetic contract tests. The injected weekday calendar is a fixture only."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import inspect
import json
import random

import pytest

from lib.pullback_observation import RULES, observe


def session(day):
    return day.weekday() < 5


def rows_for(tail, baseline=64):
    values = [100.0] * baseline + list(tail)
    day = date(2025, 1, 2)
    rows = []
    for value in values:
        while not session(day):
            day += timedelta(days=1)
        rows.append((day.isoformat(), value))
        day += timedelta(days=1)
    return rows


def result(rows, **kwargs):
    return observe(rows, expected_session=date.fromisoformat(rows[-1][0]),
                   is_session=kwargs.pop("is_session", session), **kwargs)


def next_session(day):
    day += timedelta(days=1)
    while not session(day):
        day += timedelta(days=1)
    return day


def test_risk_score_is_not_a_classifier_input():
    assert "risk_score" not in inspect.signature(observe).parameters
    read = result(rows_for([100.0] * 10))
    assert read["phase"] == "monitoring" and read["active"] is False
    assert read["drawdown_pct"] == 0
    assert "probability" not in read and "new_entry_permission" not in read


def test_two_closed_observations_confirm_without_backdating():
    rows = rows_for([97.0, 96.0])
    first = result(rows[:-1])
    assert first["phase"] == "developing" and first["active"] is False
    read = result(rows)
    assert read["phase"] == "underway" and read["active"] is True
    assert read["onset_session"] == rows[-1][0]
    assert read["observed_closes_since_onset"] == 1
    assert read["drawdown_pct"] == -4.0


def test_single_five_percent_shock_is_already_observed():
    read = result(rows_for([95.0]))
    assert read["active"] is True and read["phase"] == "underway"
    assert read["drawdown_pct"] == -5.0


def test_gap_cannot_manufacture_two_session_confirmation():
    rows = rows_for([97.0, 96.5, 96.0])
    rows.pop(-2)
    read = result(rows)
    assert read["phase"] == "developing" and read["active"] is False
    assert read["contiguous_closes"] == 1
    rows[-1] = (rows[-1][0], 94.9)
    assert result(rows)["active"] is True  # current five-percent damage is sufficient


def test_first_bounce_is_not_recovery_or_a_probability():
    read = result(rows_for([95.0, 90.0, 92.0]))
    assert read["phase"] == "underway"
    assert read["loss_recovered_pct"] == 20.0
    assert read["drawdown_pct"] == -8.0


def test_stabilization_then_failed_repair_keeps_the_same_reference():
    rows = rows_for([95.0, 90.0, 91.0, 92.0, 93.0])
    stable = result(rows)
    assert stable["phase"] == "stabilizing" and stable["active"] is True
    rows.append((next_session(date.fromisoformat(rows[-1][0])).isoformat(), 89.0))
    failed = result(rows)
    assert failed["phase"] == "underway"
    assert failed["peak_session"] == stable["peak_session"]
    assert failed["onset_session"] == stable["onset_session"]
    assert failed["loss_recovered_pct"] == 0.0
    assert failed["no_new_low_closes"] == 0


def test_sustained_price_repair_is_distinct_from_reclaiming_peak():
    read = result(rows_for([95.0, 80.0] + [81.0 + i * 0.25 for i in range(24)]))
    assert read["phase"] == "recovering" and read["active"] is True
    assert read["drawdown_pct"] < 0
    assert read["resolution"] is None


def test_one_reclaimed_close_cannot_resolve_a_decline():
    rows = rows_for([95.0, 90.0, 100.0, 100.2])
    one = result(rows[:-1])
    assert one["phase"] == "recovering" and one["active"] is True
    two = result(rows)
    assert two["phase"] == "repaired" and two["active"] is False
    assert two["resolution"] == "prior_high_reclaimed"
    assert two["drawdown_pct"] == 0 and two["loss_recovered_pct"] == 100


def test_missing_close_resets_peak_reclaim_confirmation():
    rows = rows_for([95.0, 90.0, 100.0, 100.1, 100.2])
    rows.pop(-2)
    read = result(rows)
    assert read["active"] is True and read["resolution"] is None


def test_peak_aging_out_is_not_recovery():
    rows = rows_for([95.0, 94.0] + [94.0] * 85)
    start = result(rows[:66])
    read = result(rows)
    assert read["active"] is True
    assert read["peak_close"] == 100.0
    assert read["peak_session"] == start["peak_session"]
    assert read["drawdown_pct"] == -6.0
    assert read["recent_63_drawdown_pct"] == 0.0
    assert read["resolution"] is None


def test_trend_repair_rearms_without_a_fake_new_pullback():
    rows = rows_for([95.0, 80.0] + [81.0 + i * 0.3 for i in range(50)])
    reads = [result(rows[:k]) for k in range(66, len(rows) + 1)]
    repaired = next(i for i, r in enumerate(reads) if r["resolution"] == "trend_repaired_below_prior_high")
    assert reads[repaired]["drawdown_pct"] < 0  # not a claim of full loss recovery
    assert all(r["active"] is False for r in reads[repaired:])
    assert reads[-1]["phase"] == "monitoring"
    assert reads[-1]["reference_reset_session"]
    assert reads[-1]["recent_63_drawdown_pct"] < 0


@pytest.mark.parametrize("value", [None, True, 0.0, -1.0, float("nan"), float("inf"), "100"])
def test_invalid_closes_never_become_zero_or_calm(value):
    read = result(rows_for([value]))
    assert read["available"] is False and read["phase"] == "unavailable"
    assert read["active"] is None and read["drawdown_pct"] is None


def test_stale_source_retains_its_clock_but_not_a_current_state():
    rows = rows_for([95.0])
    end = next_session(date.fromisoformat(rows[-1][0]))
    read = observe(rows, expected_session=end, is_session=session)
    assert read["quality"] == "delayed" and read["phase"] == "unavailable"
    assert read["asof"] == rows[-1][0]
    assert read["drawdown_pct"] is None and read["active"] is None
    assert read["last_observation"]["phase"] == "underway"


def test_identical_duplicate_is_not_a_second_observed_close():
    rows = rows_for([97.0])
    rows.append(rows[-1])
    read = result(rows)
    assert read["phase"] == "developing"
    assert read["collapsed_identical_duplicates"] == 1
    rows.append((rows[-1][0], 96.0))
    assert result(rows)["quality"] == "conflicting_duplicate"


def test_intraday_timestamp_is_not_a_daily_close_label():
    rows = rows_for([95.0])
    day = date.fromisoformat(rows[-1][0])
    rows[-1] = (rows[-1][0] + "T14:00:00", 95.0)
    assert observe(rows, expected_session=day, is_session=session)["quality"] == "invalid_session_label"


def test_empty_and_short_history_are_explicit():
    day = date(2025, 1, 2)
    assert observe([], expected_session=day, is_session=session)["quality"] == "no_history"
    assert result(rows_for([], baseline=62))["quality"] == "insufficient_history"
    assert observe([], expected_session=date(2025, 1, 4), is_session=session)["quality"] == "invalid_expected_session"


def test_input_is_not_mutated_and_order_is_irrelevant():
    rows = rows_for([97.0, 96.0, 94.0])
    before = deepcopy(rows)
    expected = date.fromisoformat(rows[-1][0])
    a = observe(rows, expected_session=expected, is_session=session)
    b = observe(list(reversed(rows)), expected_session=expected, is_session=session)
    assert a == b and rows == before
    json.dumps(a, allow_nan=False)


def test_prefix_causality_and_no_backdated_future_transition():
    rng = random.Random(817)
    prices = [100.0]
    for _ in range(165):
        prices.append(prices[-1] * (1 + rng.uniform(-0.022, 0.022)))
    rows = rows_for(prices, baseline=0)
    keys = ["phase", "active", "drawdown_pct", "peak_session", "onset_session",
            "loss_recovered_pct", "price_transitions", "price_path", "source_digest"]
    for k in range(64, len(rows), 3):
        end = date.fromisoformat(rows[k - 1][0])
        prefix = observe(rows[:k], expected_session=end, is_session=session)
        full = observe(rows, expected_session=end, is_session=session)
        assert {key: prefix[key] for key in keys} == {key: full[key] for key in keys}
        assert all(row["date"] <= end.isoformat() for row in full["timeline"])
        assert full["excluded_future_rows"] == len(rows) - k


def test_future_bad_values_are_not_evidence_today():
    rows = rows_for([97.0, 96.0])
    end = date.fromisoformat(rows[-1][0])
    a = observe(rows, expected_session=end, is_session=session)
    rows.append((next_session(end).isoformat(), float("inf")))
    b = observe(rows, expected_session=end, is_session=session)
    assert a["source_digest"] == b["source_digest"]
    assert a["phase"] == b["phase"]


def test_calendar_disagreement_in_selected_evidence_blocks_state():
    rows = rows_for([95.0, 94.0])
    closed = date.fromisoformat(rows[-2][0])
    read = result(rows, is_session=lambda day: session(day) and day != closed)
    assert read["quality"] == "calendar_disagreement"
    assert read["phase"] == "unavailable" and read["active"] is None


def test_archival_calendar_mismatch_is_reported_not_erased():
    rows = rows_for([100.0] * 70)
    closed = date.fromisoformat(rows[1][0])
    read = result(rows, is_session=lambda day: session(day) and day != closed)
    assert read["available"] is True and read["phase"] == "monitoring"
    assert read["sample_count"] == len(rows)
    assert read["calendar_disagreement_count"] == 1
    assert read["last_calendar_disagreement"] == rows[1][0]


def test_old_calendar_conflict_cannot_escape_by_aging_off_the_chart():
    rows = rows_for([120.0, 90.0] + [90.0] * 85)
    closed = date.fromisoformat(rows[64][0])
    read = result(rows, is_session=lambda day: session(day) and day != closed)
    assert read["quality"] == "calendar_disagreement"


def test_rules_are_versioned_descriptions_not_fitted_probabilities():
    assert RULES.version == "close_path.v1"
    assert RULES.onset_drawdown == 0.02 and RULES.shock_drawdown == 0.05
    assert RULES.reference_closes == 63


def test_exactly_63_closes_is_sufficient_for_a_reference_state():
    values = [100.0] * 62 + [98.0]
    day = date(2025, 1, 2)
    rows = []
    for value in values:
        while not session(day):
            day += timedelta(days=1)
        rows.append((day.isoformat(), value))
        day += timedelta(days=1)
    read = result(rows)
    assert read["available"] is True
    assert read["phase"] == "developing"
    assert read["drawdown_pct"] == -2.0
    assert read["recent_63_drawdown_pct"] == -2.0
    assert read["peak_close"] == 100.0


def test_reference_window_is_exactly_63_closes_not_64():
    # The 110 high is the 64th close from the latest row. The penultimate
    # 109 close is less than 2% below it, so no episode existed before the
    # boundary. On the latest row the exact 63-close window ages 110 out:
    # 104.5 is a developing decline from 109, while retaining a 64th close
    # would incorrectly turn the same row into a >=5% shock from 110.
    values = [110.0] + [100.0] * 61 + [109.0, 104.5]
    day = date(2025, 1, 2)
    rows = []
    for value in values:
        while not session(day):
            day += timedelta(days=1)
        rows.append((day.isoformat(), value))
        day += timedelta(days=1)
    read = result(rows)
    assert read["phase"] == "developing"
    assert read["active"] is False
    assert read["drawdown_pct"] == -4.1284
    assert read["recent_63_drawdown_pct"] == -4.1284
    assert read["peak_close"] == 109.0
    assert read["peak_session"] == rows[-2][0]
    assert read["peak_session"] != rows[0][0]
    assert read["onset_session"] is None
