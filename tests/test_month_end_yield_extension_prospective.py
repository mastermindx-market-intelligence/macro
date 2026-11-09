from __future__ import annotations

from datetime import date

import pandas as pd

from research.rates_direction import month_end_yield_extension_prospective as p


def test_frozen_schedule_is_deterministic_next_24_month_ends():
    schedule = p.frozen_schedule()
    assert len(schedule) == 24
    assert schedule[0] == "2026-09-30"
    assert schedule == sorted(schedule)
    assert len(set(schedule)) == 24
    assert all(date.fromisoformat(x) > p.FREEZE_DATE for x in schedule)


def test_evaluate_event_uses_exact_event_date_and_same_month_prior_changes():
    idx = pd.to_datetime(
        [
            "2026-09-24",
            "2026-09-25",
            "2026-09-28",
            "2026-09-29",
            "2026-09-30",
        ]
    )
    s = pd.Series([5.00, 5.01, 5.02, 5.03, 5.00], index=idx)
    event = p.evaluate_event(s, date(2026, 9, 30))
    assert event["status"] == "MATURED"
    assert event["quarter_end_month"] is True
    assert event["signal"] == "DOWN"
    assert round(event["raw_bp"], 8) == -3.0
    # Prior same-month daily changes are +1,+1,+1 bp.
    assert round(event["other_month_mean_bp"], 8) == 1.0
    assert round(event["excess_bp"], 8) == -4.0
    assert event["directional_success"] is True
    assert event["authority"] is False


def test_missing_frozen_event_date_is_not_substituted():
    idx = pd.to_datetime(["2026-09-29", "2026-10-01"])
    s = pd.Series([5.00, 4.95], index=idx)
    event = p.evaluate_event(s, date(2026, 9, 30))
    assert event["status"] == "MISSING_FROZEN_EVENT_OBSERVATION"
    assert event["raw_bp"] is None


def test_future_event_stays_pending():
    idx = pd.to_datetime(["2026-09-29", "2026-09-30"])
    s = pd.Series([5.0, 4.99], index=idx)
    event = p.evaluate_event(s, date(2026, 10, 30))
    assert event["status"] == "PENDING_SOURCE"


def test_zero_change_is_not_directional_success():
    idx = pd.to_datetime(
        ["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30"]
    )
    s = pd.Series([5.0, 5.0, 5.0, 5.0, 5.0], index=idx)
    event = p.evaluate_event(s, date(2026, 10, 30))
    assert event["status"] == "MATURED"
    assert event["raw_bp"] == 0.0
    assert event["directional_success"] is False


def test_prefix_digest_is_ordered_value_sensitive_and_cutoff_bounded():
    idx = pd.to_datetime(["2026-09-21", "2026-09-22", "2026-09-23"])
    s = pd.Series([4.9, 5.0, 5.1], index=idx)
    a = p.series_prefix_digest(s, date(2026, 9, 22))
    changed_future = s.copy()
    changed_future.iloc[-1] = 9.9
    assert p.series_prefix_digest(changed_future, date(2026, 9, 22)) == a
    changed_prefix = s.copy()
    changed_prefix.iloc[1] = 4.8
    assert p.series_prefix_digest(changed_prefix, date(2026, 9, 22)) != a


def _matured(i: int, raw: float, excess: float, quarter=False):
    return {
        "event_date": f"202{7 + i // 12}-{(i % 12) + 1:02d}-28",
        "quarter_end_month": quarter,
        "signal": "DOWN",
        "status": "MATURED",
        "raw_bp": raw,
        "excess_bp": excess,
        "directional_success": raw < 0,
        "authority": False,
    }


def test_summary_cannot_promote_below_24_events():
    events = [_matured(i, -1.0, -1.0, quarter=(i % 3 == 0)) for i in range(12)]
    got = p.summarize(events, historical_prefix_changed=False)
    assert got["descriptive_floor_met"] is True
    assert got["promotion_review_sample_met"] is False
    assert got["promotion_gate_met"] is False
    assert got["directional_hit_fraction"] == 1.0


def test_summary_gate_requires_unchanged_prefix_and_both_negative_metrics():
    events = [_matured(i, -1.0, -1.2, quarter=(i % 3 == 0)) for i in range(24)]
    passed = p.summarize(events, historical_prefix_changed=False)
    assert passed["promotion_review_sample_met"] is True
    assert passed["promotion_gate_met"] is True

    changed = p.summarize(events, historical_prefix_changed=True)
    assert changed["promotion_gate_met"] is False

    wrong = [_matured(i, -1.0, 1.0) for i in range(24)]
    assert p.summarize(wrong, historical_prefix_changed=False)["promotion_gate_met"] is False


def test_quarter_end_is_diagnostic_only_not_signal_variant():
    event = _matured(0, 1.0, 1.0, quarter=True)
    assert event["signal"] == "DOWN"
    got = p.summarize([event], historical_prefix_changed=False)
    assert got["quarter_end_diagnostic"]["n"] == 1
    assert got["non_quarter_end_diagnostic"]["n"] == 0


def test_spec_reuses_existing_family_and_has_no_authority():
    assert p.FAMILY == "d2_rates_calendar_flows"
    assert p.PRIOR_FAMILY_TRIALS == 21
    assert p.SPEC["authority"] is False
    assert p.SPEC["quarter_end_is_diagnostic_only"] is True
