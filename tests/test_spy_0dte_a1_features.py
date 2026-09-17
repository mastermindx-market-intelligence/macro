import math
import sys
from pathlib import Path

RESEARCH = Path(__file__).parents[1] / "scripts" / "research"
sys.path.insert(0, str(RESEARCH))
import spy_0dte_a1_features as f

DATE = "2025-07-01"


def payload(
    prices=None,
    iv_open=0.30,
    iv_decision=0.25,
    iv_error=0.0,
    decision="09:45:00.000",
):
    if prices is None:
        prices = {}
        for i in range(31):
            h = 9 + (30 + i) // 60
            m = (30 + i) % 60
            prices[f"{h:02d}:{m:02d}:00.000"] = 100 + i * 0.1
    rows = []
    for clock, px in prices.items():
        iv = 0.2
        if clock == "09:30:00.000":
            iv = iv_open
        if clock == decision:
            iv = iv_decision
        rows.append(
            {
                "timestamp": DATE + "T" + clock,
                "underlying_timestamp": DATE + "T" + clock,
                "underlying_price": px,
                "implied_vol": iv,
                "iv_error": iv_error,
            }
        )
    return {
        "response": [
            {
                "contract": {
                    "symbol": "SPY",
                    "expiration": DATE,
                    "strike": 600.0,
                    "right": "PUT",
                },
                "data": rows,
            },
            {
                "contract": {
                    "symbol": "SPY",
                    "expiration": DATE,
                    "strike": 602.0,
                    "right": "CALL",
                },
                "data": [dict(row) for row in rows],
            },
        ]
    }


def fixture():
    return {"events": {"2025": {"CPI": [DATE], "PPI": [], "NFP": [], "FOMC": []}}}


def build(p, clock="09:45:00.000"):
    return f.build_a1_features(
        session_date=DATE,
        decision_clock=clock,
        greeks_payload=p,
        short_right="P",
        short_strike=600,
        event_fixture=fixture(),
    )


def test_0935_cannot_see_15m_or_30m():
    features = build(payload(decision="09:35:00.000"), "09:35:00.000")
    assert features["first_5m_return"] is not None
    assert features["first_15m_return"] is None
    assert features["first_30m_return"] is None
    assert features["decision_minutes_from_open"] == 5


def test_0945_sees_first_5_and_15_but_not_30():
    features = build(payload(decision="09:45:00.000"))
    assert math.isclose(features["first_5m_return"], 100.5 / 100 - 1)
    assert math.isclose(features["first_15m_return"], 101.5 / 100 - 1)
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
        prices[f"{h:02d}:{m:02d}:00.000"] = 100 + i * 0.1
    features = build(payload(prices=prices, decision="09:45:00.000"))
    assert features["first_15m_return"] is not None
    assert features["realized_vol_open_to_decision"] is None


def test_exact_short_iv_and_bad_iv_fail_closed_to_null():
    features = build(payload(iv_open=0.30, iv_decision=0.25))
    assert features["short_iv_level"] == 0.25
    assert math.isclose(features["short_iv_change_from_open"], -0.05)
    bad = build(payload(iv_error=100.0))
    assert bad["short_iv_level"] is None
    assert bad["short_iv_change_from_open"] is None


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
    p["response"][1]["data"][0]["underlying_price"] += 0.01
    try:
        f.collapse_underlying_prices(p, DATE)
    except f.FeatureError as exc:
        assert "disagree" in str(exc)
    else:
        raise AssertionError("cross-contract disagreement accepted")


def test_events_gap_null_and_no_forbidden_fields():
    features = build(payload(decision="09:35:00.000"), "09:35:00.000")
    assert features["event_cpi"] == 1 and features["event_high_impact_any"] == 1
    assert features["gap_return"] is None and features["gap_direction"] is None
    forbidden = ("gamma", "gex", "pnl", "profit", "stop", "outcome", "label")
    assert not any(any(token in key.lower() for token in forbidden) for key in features)
