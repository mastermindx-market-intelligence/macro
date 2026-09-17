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


def fixture():
    return {"events": {"2025": {"CPI": [DATE], "PPI": [], "NFP": [], "FOMC": []}}}


def build(p, clock="09:45:00.000", prior_close=None):
    return f.build_a1_features(
        session_date=DATE,
        decision_clock=clock,
        iv_payload=p,
        event_fixture=fixture(),
        prior_close=prior_close,
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


def test_realized_vol_nulls_if_any_required_minute_missing():
    prices = {}
    for i in range(16):
        h = 9 + (30 + i) // 60
        m = (30 + i) % 60
        if i == 7:
            continue
        prices[f"{h:02d}:{m:02d}:00.000"] = 600 + i * .01
    features = build(payload(prices=prices, decision="09:45:00.000"))
    assert features["first_15m_return"] is not None
    assert features["realized_vol_open_to_decision"] is None


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
    assert features["realized_vol_open_to_decision"] is None
    assert features["atm_iv_level"] is not None
    assert features["atm_iv_change_from_first_valid"] is not None


def test_one_invalid_underlying_peer_does_not_poison_valid_same_minute_rows():
    p = payload(decision="09:35:00.000")
    p["response"][0]["data"][2]["underlying_price"] = 0.0
    prices = f.collapse_underlying_prices(p, DATE)
    assert math.isclose(prices["09:32:00.000"], 600.02)

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
