"""Future-low research labels: causal origin, exact maturity, no invented forecasts."""
from datetime import date

import pytest

from lib import nyse_calendar as cal
from research.grey_deer.pullback_forward_minimum_labels import label_forward_minimum


@pytest.mark.parametrize("horizon,expected", [
    (1, 0.04), (2, 0.04),
])
def test_nyse_holiday_does_not_count_as_session(horizon, expected):
    # Friday 2026-07-03 was the observed July Fourth NYSE holiday.
    prices = [
        ("2026-07-02", 100.0), ("2026-07-06", 96.0),
        ("2026-07-07", 102.0)
    ]
    out = label_forward_minimum(prices, origin="2026-07-02",
                                horizon_sessions=horizon, is_session=cal.is_session)
    assert out["schema"] == "pullback_future_minimum_label.v1"
    assert out["matured"] is True
    assert out["additional_loss_fraction"] == pytest.approx(expected)
    assert out["target_end"] == ("2026-07-06" if horizon == 1 else "2026-07-07")
    assert out["minimum_close"] == 96.0


def test_rebound_with_no_new_low_has_zero_additional_loss():
    rows = [("2026-10-08", 93.2), ("2026-10-09", 94.1)]
    out = label_forward_minimum(rows, origin="2026-10-08",
                                horizon_sessions=1, is_session=cal.is_session)
    assert out["additional_loss_fraction"] == 0
    assert out["minimum_close"] == 93.2


def test_immature_horizon_is_censored_not_a_partial_label():
    rows = [("2026-07-02", 100.0), ("2026-07-06", 95.0)]
    out = label_forward_minimum(rows, origin="2026-07-02",
                                horizon_sessions=2, is_session=cal.is_session)
    assert out["matured"] is False
    assert out["reason"] == "label_not_mature"
    assert out["additional_loss_fraction"] is None


def test_missing_interior_session_does_not_manufacture_low():
    rows = [("2026-07-02", 100.0), ("2026-07-07", 80.0)]
    out = label_forward_minimum(rows, origin="2026-07-02",
                                horizon_sessions=2, is_session=cal.is_session)
    assert out["matured"] is False
    assert out["reason"] == "missing_session"
    assert out["additional_loss_fraction"] is None


@pytest.mark.parametrize("bad_rows", [
    [("2026-07-02", 100.0), ("2026-07-06", 0)],
    [("2026-07-02", 100.0), ("2026-07-06", -10)],
    [("2026-07-02", 100.0), ("2026-07-06", float("nan"))],
    [("2026-07-02", 100.0), ("2026-07-06", True)],
    [("2026-07-02", 100.0), ("2026-07-06", 93), ("2026-07-06", 92)],
    [("2026-07-02", 100.0), ("2026-07-06T15:00:00", 92)],
])
def test_invalid_price_or_ambiguous_session_is_not_a_valid_label(bad_rows):
    out = label_forward_minimum(bad_rows, origin="2026-07-02",
                                horizon_sessions=1, is_session=cal.is_session)
    assert not out["matured"]
    assert out["additional_loss_fraction"] is None
    assert out["reason"] in {"invalid_price", "ambiguous_session"}


@pytest.mark.parametrize("origin,horizon", [
    ("2026-07-03", 1), ("2026-07-02", 0), ("2026-07-02", -1),
    ("2026-07-02", 1.5), ("2026-07-02", True),
])
def test_invalid_origin_or_horizon_rejected(origin, horizon):
    with pytest.raises(ValueError):
        label_forward_minimum([("2026-07-02", 100.0)],
                              origin=origin, horizon_sessions=horizon,
                              is_session=cal.is_session)


def test_no_knowledge_from_after_the_horizon_or_from_late_future_revision():
    rows = [
        ("2026-07-02", 100.0), ("2026-07-06", 96.0),
        ("2026-07-07", 105.0), ("2026-07-08", 60.0),
    ]
    label = label_forward_minimum(rows, origin="2026-07-02",
                                  horizon_sessions=2, is_session=cal.is_session)
    assert label["additional_loss_fraction"] == pytest.approx(0.04)
    assert label["target_end"] == "2026-07-07"


def test_nested_horizons_widen_or_hold_not_improve_when_mature():
    rows = [
        ("2026-07-02", 100.0), ("2026-07-06", 99.0),
        ("2026-07-07", 95.0), ("2026-07-08", 97.0),
    ]
    losses = [label_forward_minimum(rows, origin="2026-07-02",
                                    horizon_sessions=h, is_session=cal.is_session)
              ["additional_loss_fraction"] for h in (1, 2, 3)]
    assert losses == sorted(losses)


def test_mixed_clock_labels_never_coerce_intraday_to_settled_day():
    rows = [("2026-07-02", 100.0), ("2026-07-06T00:00:00", 96)]
    out = label_forward_minimum(rows, origin="2026-07-02",
                                horizon_sessions=1, is_session=cal.is_session)
    assert not out["matured"] and out["reason"] == "ambiguous_session"
