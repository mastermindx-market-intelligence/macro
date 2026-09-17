import math
import sys
from pathlib import Path

RESEARCH = Path(__file__).parents[1] / "scripts" / "research"
sys.path.insert(0, str(RESEARCH))
import spy_0dte_a1_features as f

DATE = "2025-07-01"


def payload(
    prices=None,
    put_iv_open=.30,
    call_iv_open=.32,
    put_iv_decision=.24,
    call_iv_decision=.26,
    iv_error=0.0,
    decision="09:45:00.000",
    bid=1.0,
    ask=1.1,
):
    if prices is None:
        prices = {}
        for i in range(31):
            h = 9 + (30 + i) // 60
            m = (30 + i) % 60
            prices[f"{h:02d}:{m:02d}:00.000"] = 600 + i * .01

    def rows_for(right):
        rows = []
        for clock, px in prices.items():
            iv = .20 if right == "PUT" else .22
            if clock == "09:30:00.000":
                iv = put_iv_open if right == "PUT" else call_iv_open
            if clock == decision:
                iv = put_iv_decision if right == "PUT" else call_iv_decision
            rows.append({
                "timestamp": DATE + "T" + clock,
                "underlying_timestamp": DATE + "T" + clock,
                "underlying_price": px,
                "implied_vol": iv,
                "iv_error": iv_error,
                "bid": bid,
                "ask": ask,
            })
        return rows

    return {"response": [
        {
            "contract": {"symbol": "SPY", "expiration": DATE, "strike": 600.0, "right": "PUT"},
            "data": rows_for("PUT"),
        },
        {
            "contract": {"symbol": "SPY", "expiration": DATE, "strike": 600.0, "right": "CALL"},
            "data": rows_for("CALL"),
        },
        {
            "contract": {"symbol": "SPY", "expiration": DATE, "strike": 602.0, "right": "CALL"},
            "data": [dict(row, implied_vol=.80) for row in rows_for("CALL")],
        },
    ]}


def bar_payload(*, missing=(), mutate=None):
    rows = []; missing = set(missing)
    cumulative_notional = 0.0; cumulative_volume = 0
    for i in range(31):
        h = 9 + (30 + i) // 60; m = (30 + i) % 60
        clock = f"{h:02d}:{m:02d}:00.000"
        if clock in missing:
            continue
        open_px = 600 + i * .01; close_px = 600 + (i + 1) * .01
        volume = 100 + i; bar_vwap = (open_px + close_px) / 2.0
        cumulative_notional += bar_vwap * volume; cumulative_volume += volume
        row = {
            "timestamp": DATE + "T" + clock, "open": open_px,
            "high": close_px + .005, "low": open_px - .005, "close": close_px,
            "volume": volume, "count": 10 + i,
            "vwap": cumulative_notional / cumulative_volume,
        }
        if mutate is not None: mutate(i, row)
        rows.append(row)
    return {"response": rows}


def fixture():
    return {"events": {"2025": {"CPI": [DATE], "PPI": [], "NFP": [], "FOMC": []}}}


def build(p, clock="09:45:00.000", prior_close=None, bars=None, prior_realized_vol=None, prior_implied_move=None):
    return f.build_a1_features(
        session_date=DATE,
        decision_clock=clock,
        iv_payload=p,
        bar_payload=bar_payload() if bars is None else bars,
        event_fixture=fixture(),
        prior_close=prior_close,
        prior_realized_vol=prior_realized_vol,
        prior_implied_move=prior_implied_move,
    )


def test_0935_cannot_see_15m_or_30m():
    features = build(payload(decision="09:35:00.000"), "09:35:00.000")
    assert features["first_5m_return"] is not None
    assert features["first_15m_return"] is None
    assert features["first_30m_return"] is None
    assert features["decision_minutes_from_open"] == 5


def test_0945_sees_first_5_and_15_but_not_30():
    features = build(payload(decision="09:45:00.000"))
    assert math.isclose(features["first_5m_return"], 600.05 / 600 - 1)
    assert math.isclose(features["first_15m_return"], 600.15 / 600 - 1)
    assert features["first_30m_return"] is None
    assert features["realized_vol_open_to_decision"] is not None


def test_1000_sees_all_frozen_horizons():
    features = build(payload(decision="10:00:00.000"), "10:00:00.000")
    assert features["first_30m_return"] is not None
    assert features["decision_minutes_from_open"] == 30


def test_realized_vol_nulls_if_any_required_completed_bar_missing():
    bars = bar_payload(missing={"09:37:00.000"})
    features = build(payload(decision="09:45:00.000"), bars=bars)
    assert features["first_15m_return"] is not None
    assert features["realized_vol_open_to_decision"] is None
    assert features["opening_range_high"] is None
    assert features["session_vwap_to_decision"] is None

def test_atm_iv_averages_call_put_and_uses_first_strictly_post_open_anchor():
    features = build(payload(
        put_iv_open=.30,
        call_iv_open=.32,
        put_iv_decision=.24,
        call_iv_decision=.26,
        decision="09:45:00.000",
    ))
    assert math.isclose(features["atm_iv_level"], .25)
    assert math.isclose(features["atm_iv_change_from_first_valid"], .04)
    assert features["atm_iv_anchor_minutes_from_open"] == 1


def test_small_solver_residual_and_frozen_boundary_are_valid():
    small = build(payload(iv_error=.0002, decision="09:45:00.000"))
    edge = build(payload(iv_error=f.IV_ERROR_MAX, decision="09:45:00.000"))
    assert small["atm_iv_level"] is not None
    assert edge["atm_iv_level"] is not None


def test_solver_residual_above_frozen_limit_fails_closed_to_null():
    bad = build(payload(iv_error=f.IV_ERROR_MAX + .0001, decision="09:45:00.000"))
    assert bad["atm_iv_level"] is None
    assert bad["atm_iv_change_from_first_valid"] is None
    assert bad["atm_iv_anchor_minutes_from_open"] is None
    catastrophic = build(payload(iv_error=100.0, decision="09:45:00.000"))
    assert catastrophic["atm_iv_level"] is None


def test_invalid_nbbo_fails_iv_closed():
    bad = build(payload(bid=0.0, ask=1.1, decision="09:45:00.000"))
    assert bad["atm_iv_level"] is None



def test_nonpositive_underlying_rows_are_null_observations_not_day_failure():
    p = payload(decision="10:00:00.000")
    for group in p["response"]:
        for row in group["data"]:
            if row["timestamp"].endswith("09:55:00.000"):
                row["underlying_price"] = 0.0
    features = build(p, "10:00:00.000")
    assert features["first_30m_return"] is not None
    assert features["realized_vol_open_to_decision"] is not None
    assert features["atm_iv_level"] is not None
    assert features["atm_iv_change_from_first_valid"] is not None


def test_one_invalid_underlying_peer_does_not_poison_valid_same_minute_rows():
    p = payload(decision="09:35:00.000")
    p["response"][0]["data"][2]["underlying_price"] = 0.0
    prices = f.collapse_underlying_prices(p, DATE)
    assert math.isclose(prices["09:32:00.000"], 600.02)

def test_future_stock_bar_schema_and_values_cannot_poison_earlier_decision():
    bars = bar_payload()
    future = next(row for row in bars["response"] if row["timestamp"].endswith("09:35:00.000"))
    future["vwap"] = 9999.0
    future["future_only_field"] = "schema drift"
    features = build(
        payload(decision="09:35:00.000"),
        "09:35:00.000",
        bars=bars,
    )
    assert features["opening_range_high"] < 601.0
    assert features["session_vwap_to_decision"] < 601.0


def test_future_iv_corruption_and_gamma_cannot_poison_earlier_decision():
    p = payload(decision="09:35:00.000")
    for group in p["response"]:
        future = next(row for row in group["data"] if row["timestamp"].endswith("09:50:00.000"))
        future["underlying_price"] = 0.0
        future["gamma"] = 999.0
    features = build(p, "09:35:00.000")
    assert features["atm_iv_level"] is not None
    assert features["expected_move_1sigma_frac"] is not None


def test_completed_bars_drive_range_vwap_and_never_read_decision_bar():
    def mutate(i, row):
        if i == 5:  # 09:35 bar is future relative to the exact 09:35 decision.
            row.update({"open": 1.0, "high": 9999.0, "low": 1.0, "close": 9999.0, "vwap": 5000.0})
    features = build(payload(decision="09:35:00.000"), "09:35:00.000", bars=bar_payload(mutate=mutate))
    assert math.isclose(features["opening_price"], 600.0)
    assert math.isclose(features["first_5m_return"], 600.05 / 600.0 - 1.0)
    assert features["opening_range_high"] < 601.0
    assert features["opening_range_low"] > 599.0
    assert features["session_vwap_to_decision"] < 601.0
    assert features["range_expansion_vs_first_5m"] == 1.0
    assert features["opening_range_5m_high"] == features["opening_range_high"]
    assert features["opening_range_15m_high"] is None


def test_vwap_distance_slope_and_expected_move_are_causal_and_finite():
    features = build(
        payload(put_iv_decision=.24, call_iv_decision=.26, decision="09:45:00.000"),
        "09:45:00.000", prior_close=599.0,
    )
    assert features["vwap_distance_frac"] is not None
    assert features["vwap_slope_5m_frac_per_min"] > 0
    assert features["opening_range_location"] is not None
    expected_frac = .25 * math.sqrt(375.0 / f.CALENDAR_MINUTES_PER_YEAR)
    assert math.isclose(features["expected_move_1sigma_frac"], expected_frac)
    assert math.isclose(features["expected_move_1sigma_abs"], features["decision_price"] * expected_frac)
    assert features["expected_move_lower"] < features["decision_price"] < features["expected_move_upper"]


def test_gap_direction_maps_to_symmetric_reversal_continuation_state():
    gap_up = build(payload(decision="09:35:00.000"), "09:35:00.000", prior_close=599.0)
    assert gap_up["gap_direction"] == 1
    assert gap_up["continuation_in_gap_direction_flag"] in {0, 1}
    assert gap_up["reversal_from_gap_extreme_flag"] in {0, 1}
    assert gap_up["continuation_in_gap_direction_flag"] + gap_up["reversal_from_gap_extreme_flag"] <= 1
    assert gap_up["gap_reversal_score"] is not None


def test_stock_bar_parser_refuses_schema_drift_and_cross_session_rows():
    bad = bar_payload(); del bad["response"][0]["vwap"]
    try:
        f.parse_underlying_bars(bad, DATE)
    except f.FeatureError as exc:
        assert "fields" in str(exc)
    else:
        raise AssertionError("stock OHLC schema drift accepted")
    bad = bar_payload(); bad["response"][0]["timestamp"] = "2025-07-02T09:30:00.000"
    try:
        f.parse_underlying_bars(bad, DATE)
    except f.FeatureError as exc:
        assert "cross-session" in str(exc)
    else:
        raise AssertionError("cross-session stock bar accepted")


def test_zero_or_invalid_stock_bar_stays_missing_not_imputed():
    def mutate(i, row):
        if i == 7:
            row["close"] = 0.0
    features = build(payload(decision="09:45:00.000"), bars=bar_payload(mutate=mutate))
    assert features["realized_vol_open_to_decision"] is None
    assert features["opening_range_high"] is None
    assert features["first_15m_return"] is not None


def test_theta_cumulative_vwap_may_be_outside_current_bar_range():
    bars = bar_payload()
    bars["response"][2]["vwap"] = 600.005  # below 09:32 bar low, but inside session range.
    parsed = f.parse_underlying_bars(bars, DATE)
    assert math.isclose(parsed["09:32:00.000"]["vwap"], 600.005)


def test_stock_bar_timestamp_without_fraction_normalizes_to_frozen_clock():
    bars = bar_payload()
    bars["response"][0]["timestamp"] = DATE + "T09:30:00"
    parsed = f.parse_underlying_bars(bars, DATE)
    assert "09:30:00.000" in parsed


def test_vwap_state_uses_last_cumulative_row_without_double_weighting():
    bars = bar_payload()
    features = build(payload(decision="09:45:00.000"), bars=bars)
    expected = next(row["vwap"] for row in bars["response"] if row["timestamp"].endswith("09:44:00.000"))
    assert math.isclose(features["session_vwap_to_decision"], expected)


def test_15m_range_becomes_available_only_at_0945_and_remains_frozen():
    early = build(payload(decision="09:35:00.000"), "09:35:00.000")
    later = build(payload(decision="09:45:00.000"), "09:45:00.000")
    assert early["opening_range_15m_high"] is None
    assert later["opening_range_5m_high"] is not None
    assert later["opening_range_15m_high"] is not None
    assert later["opening_range_15m_high"] >= later["opening_range_5m_high"]


def test_optional_gap_normalizers_are_signed_preopen_scales_or_null():
    missing = build(payload(decision="09:35:00.000"), "09:35:00.000", prior_close=599.0)
    assert missing["gap_vs_prior_realized_vol"] is None
    assert missing["gap_vs_prior_implied_move"] is None
    scaled = build(
        payload(decision="09:35:00.000"), "09:35:00.000", prior_close=599.0,
        prior_realized_vol=.01, prior_implied_move=.02,
    )
    assert math.isclose(scaled["gap_vs_prior_realized_vol"], scaled["gap_return"] / .01)
    assert math.isclose(scaled["gap_vs_prior_implied_move"], scaled["gap_return"] / .02)


def test_fractional_volume_or_count_refuses_structural_source_drift():
    bars = bar_payload(); bars["response"][0]["volume"] = 1.5
    try:
        f.parse_underlying_bars(bars, DATE)
    except f.FeatureError as exc:
        assert "volume/count" in str(exc)
    else:
        raise AssertionError("fractional stock volume accepted")


def test_impossible_cumulative_vwap_refuses():
    bars = bar_payload(); bars["response"][3]["vwap"] = 9999.0
    try:
        f.parse_underlying_bars(bars, DATE)
    except f.FeatureError as exc:
        assert "cumulative" in str(exc)
    else:
        raise AssertionError("impossible cumulative VWAP accepted")


def test_future_underlying_timestamp_refuses():
    p = payload(decision="09:35:00.000")
    p["response"][0]["data"][0]["underlying_timestamp"] = DATE + "T09:31:00.000"
    try:
        f.collapse_underlying_prices(p, DATE)
    except f.FeatureError as exc:
        assert "future" in str(exc)
    else:
        raise AssertionError("future underlying price accepted")


def test_cross_contract_underlying_disagreement_refuses():
    p = payload(decision="09:35:00.000")
    p["response"][1]["data"][0]["underlying_price"] += .01
    try:
        f.collapse_underlying_prices(p, DATE)
    except f.FeatureError as exc:
        assert "disagree" in str(exc)
    else:
        raise AssertionError("cross-contract disagreement accepted")


def test_gamma_bearing_source_payload_refuses():
    p = payload(decision="09:35:00.000")
    p["response"][0]["data"][0]["gamma"] = .01
    try:
        f.collapse_underlying_prices(p, DATE)
    except f.FeatureError as exc:
        assert "gamma" in str(exc).lower()
    else:
        raise AssertionError("gamma-bearing A1 payload accepted")


def test_gap_uses_explicit_prior_session_raw_close():
    features = build(payload(decision="09:35:00.000"), "09:35:00.000", prior_close=599.0)
    expected = 600.0 / 599.0 - 1.0
    assert math.isclose(features["gap_return"], expected)
    assert features["gap_direction"] == 1


def test_missing_gap_stays_null_and_corrupt_close_refuses():
    missing = build(payload(decision="09:35:00.000"), "09:35:00.000")
    assert missing["gap_return"] is None and missing["gap_direction"] is None
    try:
        build(payload(decision="09:35:00.000"), "09:35:00.000", prior_close=-1)
    except f.FeatureError as exc:
        assert "prior close" in str(exc)
    else:
        raise AssertionError("corrupt prior close accepted")


def test_events_and_no_forbidden_fields():
    features = build(payload(decision="09:35:00.000"), "09:35:00.000", prior_close=599.0)
    assert features["event_cpi"] == 1 and features["event_high_impact_any"] == 1
    forbidden = ("gamma", "gex", "pnl", "profit", "stop", "outcome", "label")
    assert not any(any(token in key.lower() for token in forbidden) for key in features)


def test_invalid_nearest_strike_does_not_fall_through_to_farther_valid_iv():
    p = payload(decision="09:45:00.000")
    for group in p["response"][:2]:
        for row in group["data"]:
            if row["timestamp"].endswith("09:45:00.000"):
                row["iv_error"] = f.IV_ERROR_MAX + .0001
    features = build(p)
    assert features["atm_iv_level"] is None
    assert features["atm_iv_change_from_first_valid"] is None


def test_one_sided_exact_atm_iv_fails_closed():
    p = payload(decision="09:45:00.000")
    for row in p["response"][0]["data"]:
        if row["timestamp"].endswith("09:45:00.000"):
            row["iv_error"] = f.IV_ERROR_MAX + .0001
    features = build(p)
    assert features["atm_iv_level"] is None
    assert features["atm_iv_change_from_first_valid"] is None
