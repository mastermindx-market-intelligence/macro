"""Falsifiers for descriptive gamma context; no data downloads or live actions."""
from datetime import datetime, timezone
import copy
import json

import pandas as pd
import pytest

from engine.market_fragility import observe

NOW = datetime(2026, 11, 13, 14, 0, tzinfo=timezone.utc)


def frame(signs=("short", "long", "short"), dates=None, **columns):
    dates = dates or ["2026-11-10", "2026-11-11", "2026-11-12"]
    return pd.DataFrame({"gamma_regime": signs, **columns}, index=pd.to_datetime(dates))


def test_two_sided_mechanism_is_not_trade_authority():
    out = observe(frame(), now=NOW, window_sessions=3)
    assert out["state"] == "amplifying"
    assert out["current"]["directional_forecast"] is None
    assert out["current"]["hedge_response"] == "with_price"
    assert out["source"]["actual_dealer_inventory_observed"] is False
    assert out["source"]["position_basis"] == "assumption"
    assert out["authority"] == {
        "display_only": True, "directional_signal": False, "ranking": False,
        "position_sizing": False, "risk_override": False, "trade_execution": False,
    }
    assert out["quality"]["predictive_validation"] == "not_established"
    assert out["quality"]["point_in_time_qualified"] is False
    assert "not a bearish forecast" in out["summary"]["en"]


def test_observed_frequencies_and_transitions():
    hist = observe(frame(), now=NOW, window_sessions=3)["history"]
    assert hist["observed_sessions"] == 3
    assert hist["short_share_observed"] == pytest.approx(2 / 3)
    assert hist["adjacent_pairs_observed"] == 2
    assert hist["sign_changes"] == 2
    assert hist["terminal_run_sessions"] == 1
    assert hist["max_long_run_sessions"] == 1
    assert hist["observed_regime_runs"] == 3
    assert hist["counts_are_independent_trials"] is False


def test_short_gamma_does_not_need_a_flip_or_negative_reported_magnitude():
    out = observe(frame(gamma_flip=[None] * 3, net_gex_bn=[15.0] * 3), now=NOW, window_sessions=3)
    assert out["state"] == "amplifying"
    assert out["current"]["gamma_flip"] is None
    assert out["current"]["reported_net_gex_bn"] == 15.0
    assert "gamma_flip_unavailable_sign_is_independent" in out["quality"]["limitations"]


def test_long_gamma_not_deduced_from_flip_position():
    out = observe(frame(signs=["long"] * 3, gamma_flip=[8000.0] * 3,
                        spot=[7000.0] * 3, dist_to_flip_pct=[-14.0] * 3), now=NOW, window_sessions=3)
    assert out["state"] == "damping"
    assert out["current"]["hedge_response"] == "against_price"
    assert "does not guarantee" in out["summary"]["en"]


@pytest.mark.parametrize("bad_sign", [None, "", "negative", "SHORT", 0, True, float("nan"), "neutral"])
def test_unknown_sign_is_not_a_benign_default(bad_sign):
    out = observe(frame(signs=["short", "short", bad_sign]), now=NOW, window_sessions=3)
    assert out["state"] == "unknown"
    assert not out["current"]["usable"]
    assert out["history"]["terminal_run_sessions"] is None
    assert "gamma_sign_unavailable" in out["quality"]["reasons"]


@pytest.mark.parametrize("input_frame", [None, pd.DataFrame(), pd.DataFrame({"net_gex_bn": [-1]}), {}])
def test_missing_or_invalid_data_is_unknown(input_frame):
    out = observe(input_frame, now=NOW, window_sessions=3)
    assert out["state"] == "unknown"
    assert out["history"]["observed_sessions"] == 0
    assert out["history"]["short_share_observed"] is None
    assert out["history"]["sign_changes"] is None
    json.dumps(out, allow_nan=False)


def test_missing_session_breaks_runs_and_transitions():
    out = observe(frame(signs=["long", "long"], dates=["2026-11-10", "2026-11-12"]), now=NOW, window_sessions=3)
    h = out["history"]
    assert out["state"] == "damping"
    assert out["data_status"] == "partial"
    assert h["observed_sessions"] == 2 and h["unknown_sessions"] == 1
    assert h["missing_sessions"] == ["2026-11-11"]
    assert h["adjacent_pairs_observed"] == 0 and h["sign_changes"] is None
    assert h["terminal_run_sessions"] == 1 and h["max_long_run_sessions"] == 1
    assert h["observed_regime_runs"] == 2


def test_stale_observation_keeps_reported_value_but_cannot_classify_today():
    out = observe(frame(signs=["short"], dates=["2026-11-10"]), now=NOW, window_sessions=3)
    assert out["state"] == "unknown" and out["data_status"] == "stale"
    assert out["current"]["reported_gamma_regime"] == "short"
    assert out["clocks"]["age_sessions"] == 2
    assert out["history"]["terminal_run_sessions"] is None


def test_today_partial_session_is_not_counted_as_a_completed_day():
    inp = frame(signs=["long", "short"], dates=["2026-11-12", "2026-11-13"])
    out = observe(inp, now=NOW, window_sessions=1)
    assert out["state"] == "amplifying"
    assert out["clocks"]["source_session_complete"] is False
    assert out["history"]["window_end"] == "2026-11-12"
    assert out["history"]["terminal_regime"] == "long"
    assert out["history"]["short_share_observed"] == 0


def test_future_source_is_not_silently_replaced_by_old_good_row():
    out = observe(frame(signs=["long", "short"], dates=["2026-11-12", "2026-11-16"]), now=NOW, window_sessions=1)
    assert out["state"] == "unknown"
    assert out["clocks"]["source_session"] == "2026-11-16"
    assert "future_source_session" in out["quality"]["reasons"]
    assert out["history"]["terminal_regime"] == "long"


def test_non_session_latest_is_not_admitted_even_when_calendar_filter_would_empty():
    now = datetime(2026, 11, 15, 14, tzinfo=timezone.utc)
    out = observe(frame(signs=["short"], dates=["2026-11-14"]), now=now, window_sessions=1)
    assert out["state"] == "unknown"
    assert "source_is_not_a_trading_session" in out["quality"]["reasons"]
    assert out["history"]["observed_sessions"] == 0


def test_old_weekend_rows_do_not_pollute_usable_history():
    inp = frame(signs=["long", "short", "short"], dates=["2026-11-08", "2026-11-11", "2026-11-12"])
    out = observe(inp, now=NOW, window_sessions=2)
    assert out["state"] == "amplifying"
    assert out["history"]["terminal_run_sessions"] == 2
    assert out["quality"]["excluded_row_counts"]["non_session"] == 1


def test_duplicate_latest_has_no_arbitrary_keep_last_winner():
    inp = frame(signs=["short", "long"], dates=["2026-11-12", "2026-11-12"])
    a = observe(inp, now=NOW, window_sessions=1)
    b = observe(inp.iloc[::-1], now=NOW, window_sessions=1)
    assert a == b
    assert a["state"] == "unknown"
    assert a["current"]["reported_gamma_regime"] is None
    assert a["history"]["observed_sessions"] == 0
    assert "ambiguous_latest_session" in a["quality"]["reasons"]


def test_duplicate_middle_session_breaks_run():
    inp = frame(signs=["short"] * 4, dates=["2026-11-10", "2026-11-11", "2026-11-11", "2026-11-12"])
    out = observe(inp, now=NOW, window_sessions=3)
    assert out["state"] == "amplifying"
    assert out["history"]["observed_sessions"] == 2
    assert out["history"]["terminal_run_sessions"] == 1
    assert out["history"]["invalid_sessions"] == ["2026-11-11"]


def test_shuffled_input_same_answer_and_no_input_mutation():
    inp = frame(spot=[7000.0] * 3)
    before = copy.deepcopy(inp)
    assert observe(inp, now=NOW) == observe(inp.iloc[::-1], now=NOW)
    pd.testing.assert_frame_equal(inp, before)


def test_invalid_session_label_cannot_be_hidden():
    inp = pd.DataFrame({"gamma_regime": ["short", "long"]}, index=["2026-11-12", "not-a-date"])
    out = observe(inp, now=NOW, window_sessions=1)
    assert out["state"] == "unknown"
    assert "invalid_session_labels" in out["quality"]["reasons"]


@pytest.mark.parametrize("numeric", [float("nan"), float("inf"), float("-inf"), True, "1.5"])
def test_nonfinite_bool_and_string_metrics_never_become_json_numbers(numeric):
    inp = frame(spot=[numeric] * 3, gamma_flip=[numeric] * 3, net_gex_bn=[numeric] * 3,
                dist_to_flip_pct=[numeric] * 3)
    out = observe(inp, now=NOW)
    assert out["current"]["spot"] is None
    assert out["current"]["gamma_flip"] is None
    assert out["current"]["reported_net_gex_bn"] is None
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize("key", ["observed_at", "available_at"])
def test_future_clock_rejects_observation(key):
    inp = frame(**{key: ["2026-11-14T20:00:00Z"] * 3})
    out = observe(inp, now=NOW, window_sessions=3)
    assert out["state"] == "unknown"
    assert f"future_{key}" in out["quality"]["reasons"]
    assert out["history"]["observed_sessions"] == 0


@pytest.mark.parametrize("stamp", ["2026-11-12T20:00:00", "garbage", 0, True])
def test_naive_or_malformed_availability_clock_not_assumed_utc(stamp):
    out = observe(frame(available_at=[stamp] * 3), now=NOW, window_sessions=3)
    assert out["state"] == "unknown"
    assert "invalid_available_at" in out["quality"]["reasons"]


def test_clock_does_not_create_pit_validation_or_rewrite_computation_time():
    inp = frame(signs=["short"], dates=["2026-11-12"],
                observed_at=["2026-11-12T20:00:00Z"], available_at=["2026-11-12T20:01:00Z"])
    out = observe(inp, now=NOW, window_sessions=1)
    assert out["state"] == "amplifying"
    assert out["clocks"]["source_available_at"] == "2026-11-12T20:01:00Z"
    assert out["clocks"]["computed_at"] == "2026-11-13T14:00:00Z"
    assert out["quality"]["point_in_time_qualified"] is False


def test_availability_cannot_precede_observation():
    inp = frame(signs=["short"], dates=["2026-11-12"],
                observed_at=["2026-11-12T21:00:00Z"], available_at=["2026-11-12T20:00:00Z"])
    out = observe(inp, now=NOW, window_sessions=1)
    assert out["state"] == "unknown"
    assert "availability_precedes_observation" in out["quality"]["reasons"]
    assert out["history"]["observed_sessions"] == 0


@pytest.mark.parametrize("window", [0, 253, -1, True, 3.0, "20"])
def test_window_configuration_fails_loud(window):
    with pytest.raises(ValueError, match="window_sessions"):
        observe(frame(), now=NOW, window_sessions=window)


def test_utc_session_label_does_not_shift_back_a_day():
    inp = frame(signs=["short"], dates=["2026-11-12T00:00:00Z"])
    out = observe(inp, now=NOW, window_sessions=1)
    assert out["clocks"]["source_session"] == "2026-11-12"
    assert out["history"]["observed_sessions"] == 1


@pytest.mark.parametrize("tier", ["thin_chain", "no_options", "invented_tier"])
def test_upstream_low_quality_is_not_upgraded(tier):
    out = observe(frame(tier=[tier] * 3), now=NOW, window_sessions=3)
    assert out["state"] == "unknown"
    assert out["current"]["source_tier"] == tier
    assert out["history"]["observed_sessions"] == 0


def test_complete_valid_tier_is_descriptive_not_predictive():
    out = observe(frame(tier=["full"] * 3), now=NOW, window_sessions=3)
    assert out["data_status"] == "ready"
    assert out["quality"]["predictive_validation"] == "not_established"
