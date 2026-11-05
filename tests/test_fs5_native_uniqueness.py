"""Synthetic native-interval falsifiers; never load market outcomes."""
import pandas as pd
import pytest

from lib.flow_score import uniqueness_weights_nyse_intervals
from lib.flow_score_geometry import GeometryError


def rows(*specs):
    return pd.DataFrame([
        {"event_id": eid, "root": root, "session_date": event,
         "fill_date": fill, "outcome_end_session": end,
         "source": "live_feed", "detector_version": "live_feed_v1",
         "model_bucket": "0_7", "evaluation_spec_version": "fs5-v1"}
        for eid, root, event, fill, end in specs
    ])


def test_holiday_and_weekend_are_not_observations():
    # Jul 3 is the observed Independence Day holiday; Jul 4/5 are a weekend.
    frame = rows(
        ("a", "AAA", "2026-07-02", "2026-07-02", "2026-07-07"),
        ("b", "BBB", "2026-07-02", "2026-07-06", "2026-07-08"),
    )
    weights = uniqueness_weights_nyse_intervals(frame)
    assert weights.to_dict() == pytest.approx({"a": 2 / 3, "b": 2 / 3})


def test_shared_endpoint_is_inclusive():
    frame = rows(
        ("a", "AAA", "2026-07-02", "2026-07-02", "2026-07-06"),
        ("b", "BBB", "2026-07-02", "2026-07-06", "2026-07-07"),
    )
    assert uniqueness_weights_nyse_intervals(frame).to_dict() == pytest.approx(
        {"a": 0.75, "b": 0.75}
    )


def test_delayed_fill_controls_units_and_support_not_event_date():
    frame = rows(
        ("a", "AAA", "2026-07-02", "2026-07-02", "2026-07-02"),
        ("b", "AAA", "2026-07-02", "2026-07-06", "2026-07-07"),
    )
    assert uniqueness_weights_nyse_intervals(frame).to_dict() == {"a": 1.0, "b": 1.0}


def test_thousand_prints_do_not_inflate_effective_support():
    original = rows(
        ("a", "AAA", "2026-07-02", "2026-07-02", "2026-07-07"),
        ("b", "BBB", "2026-07-02", "2026-07-06", "2026-07-08"),
    )
    burst = pd.concat([
        original.iloc[[0]].assign(event_id=f"a{i}") for i in range(1000)
    ] + [original.iloc[[1]]], ignore_index=True)
    before, after = map(uniqueness_weights_nyse_intervals, (original, burst))
    assert after.sum() == pytest.approx(before.sum())
    assert after.drop("b").sum() == pytest.approx(before["a"])
    assert after["a0"] == pytest.approx(before["a"] / 1000)
    assert after["b"] == pytest.approx(before["b"])


def test_same_unit_cannot_have_inconsistent_native_endpoints():
    frame = rows(
        ("a", "AAA", "2026-07-02", "2026-07-02", "2026-07-06"),
        ("b", "AAA", "2026-07-02", "2026-07-02", "2026-07-07"),
    )
    with pytest.raises(GeometryError, match="uniqueness_unit_boundary_mismatch"):
        uniqueness_weights_nyse_intervals(frame)


@pytest.mark.parametrize("field,value,error", [
    ("fill_date", None, "identity_missing:fill_date"),
    ("outcome_end_session", None, "identity_missing:outcome_end_session"),
    ("fill_date", "2026-07-03", "not_nyse_session"),
    ("outcome_end_session", "2026-07-05", "not_nyse_session"),
    ("outcome_end_session", "garbage", "outcome_end_session_invalid"),
    ("outcome_end_session", "2026-07-01", "boundary_noncausal_end"),
    ("evaluation_spec_version", "unknown", "identity_unknown_spec"),
])
def test_invalid_native_boundaries_have_no_fallback(field, value, error):
    frame = rows(("a", "AAA", "2026-07-02", "2026-07-02", "2026-07-07"))
    frame.loc[0, field] = value
    with pytest.raises(GeometryError, match=error):
        uniqueness_weights_nyse_intervals(frame)


def test_duplicate_ids_cannot_overwrite_weight():
    frame = rows(
        ("a", "AAA", "2026-07-02", "2026-07-02", "2026-07-07"),
        ("a", "BBB", "2026-07-02", "2026-07-06", "2026-07-08"),
    )
    with pytest.raises(GeometryError, match="identity_duplicate_event_id"):
        uniqueness_weights_nyse_intervals(frame)


def test_order_and_original_index_cannot_change_weights():
    frame = rows(
        ("a", "AAA", "2026-07-02", "2026-07-02", "2026-07-07"),
        ("b", "BBB", "2026-07-02", "2026-07-06", "2026-07-08"),
    )
    reordered = frame.iloc[::-1].set_axis([37, 11])
    assert uniqueness_weights_nyse_intervals(reordered).to_dict() == pytest.approx(
        uniqueness_weights_nyse_intervals(frame).to_dict()
    )



def test_disjoint_unit_after_fractional_concurrency_retains_exact_full_support():
    frame = rows(
        ("a", "AAA", "2026-07-02", "2026-07-02", "2026-07-07"),
        ("b", "BBB", "2026-07-02", "2026-07-06", "2026-07-08"),
        ("c", "CCC", "2026-07-02", "2026-07-07", "2026-07-09"),
        ("d", "DDD", "2026-07-10", "2026-07-10", "2026-07-17"),
    )
    assert uniqueness_weights_nyse_intervals(frame)["d"] == 1.0
