"""C19 WP09 pins: non-consensus record classes stay off the k3e surface."""
from engine.k3e_expectation_surface import (
    CONSENSUS_RECORD_CLASSES, NON_CONSENSUS_RECORD_CLASS)
from tests.test_k3e_expectation_surface import capture, inspect, payload, selected


def _guidance():
    g, ga = capture("guid", "2026-10-02T11:00:00Z", value=9.99)
    for row in g:
        row["provider_record_class"] = "earnings_guidance"
    return g, ga


def _selected_ids(result):
    latest = selected(result, "latest_captured_snapshot")
    supported = selected(result)
    return (
        latest["observation_id"] if latest else None,
        supported["observation_id"] if supported else None,
        result["normalized_baseline"]["candidate_observation_id"],
    )


def test_guidance_row_is_excluded_with_reason_code():
    assert "earnings_guidance" not in CONSENSUS_RECORD_CLASSES
    g, ga = _guidance()
    r, a = capture()
    for result in (payload(g, ga), payload(r + g, a + ga)):
        denominators = result["denominators"]
        assert denominators["reason_counts"][NON_CONSENSUS_RECORD_CLASS] == 2
        assert denominators["invalid_or_inconsistent_excluded_records"] == 2
        for observation_id in _selected_ids(result):
            assert observation_id is None or not str(observation_id).startswith("guid")
    alone = payload(g, ga)
    assert selected(alone, "latest_captured_snapshot") is None
    assert selected(alone) is None
    assert alone["normalized_baseline"]["candidate_observation_id"] is None
    assert alone["period_continuity"] == "ANCHOR_UNAVAILABLE"


def test_guidance_row_never_supersedes_consensus():
    r, a = capture()
    g, ga = _guidance()
    result = payload(r + g, a + ga)
    latest = selected(result, "latest_captured_snapshot")
    assert latest["observation_id"] == "one-average"
    assert latest["value"] == 2.5
    supported = selected(result)
    assert supported["observation_id"] == "one-average"
    assert supported["value"] == 2.5
    assert result["normalized_baseline"]["candidate_observation_id"] == "one-average"
    assert result["period_continuity"] == "SAME_NATIVE_PERIOD"


def test_null_anchor_surfaces_anchor_unavailable():
    rows, attempts = capture(period=None)
    newer, receipts = capture("two", "2026-10-02T11:00:00Z",
                              status="partial", period="2026-12-31")
    assert payload(rows + newer, attempts + receipts)["period_continuity"] == (
        "ANCHOR_UNAVAILABLE")
    partial, partial_attempts = capture(status="partial")
    assert payload(partial, partial_attempts)["period_continuity"] == "ANCHOR_UNAVAILABLE"


def test_anchored_rows_unchanged_by_guidance_guard():
    rows, attempts = capture()
    result = payload(rows, attempts)
    assert selected(result, "latest_captured_snapshot")["observation_id"] == "one-average"
    assert selected(result)["observation_id"] == "one-average"
    assert result["period_continuity"] == "SAME_NATIVE_PERIOD"
    assert result["denominators"]["invalid_or_inconsistent_excluded_records"] == 0
    assert NON_CONSENSUS_RECORD_CLASS not in result["denominators"]["reason_counts"]

    revenue, revenue_attempts = capture("rev")
    for row in revenue:
        row["provider_record_class"] = "revenue_estimate"
        row["metric"] = "revenue"
    result = payload(revenue, revenue_attempts, metric="revenue")
    assert selected(result, "latest_captured_snapshot")["observation_id"] == "rev-average"
    assert selected(result)["observation_id"] == "rev-average"
    assert result["period_continuity"] == "SAME_NATIVE_PERIOD"
    assert result["denominators"]["invalid_or_inconsistent_excluded_records"] == 0
    assert NON_CONSENSUS_RECORD_CLASS not in result["denominators"]["reason_counts"]
