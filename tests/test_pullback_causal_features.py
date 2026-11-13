"""Research-only causal pullback features; synthetic close sequences, no licensed feed."""
from datetime import date, timedelta
from math import sqrt
from statistics import pstdev

import pytest

from lib import nyse_calendar
from research.grey_deer.pullback_causal_features import extract_causal_features


def fixtures(n=36):
    days = []
    d = date(2026, 7, 1)
    while len(days) < n:
        if nyse_calendar.is_session(d):
            days.append(d)
        d += timedelta(days=1)
    closes = [100 * (0.998 ** i) for i in range(n)]
    rows = [(d.isoformat(), p) for d, p in zip(days, closes)]
    asof = rows[-1][0]
    obs = {
        "schema": "pullback_observation.v1",
        "market": "us",
        "benchmark": "SPY",
        "price_basis": "split_adjusted_dividend_unadjusted_close",
        "available": True,
        "quality": "current",
        "clock": "settled_close",
        "phase": "underway",
        "active": True,
        "asof": asof,
        "expected_session": asof,
        "close": closes[-1],
        "peak_close": 101.0,
        "low_close": min(closes),
        "observed_closes_since_onset": 9,
        "source_digest": "a" * 64,
    }
    return rows, obs


def extract(rows=None, obs=None):
    if rows is None or obs is None:
        r, o = fixtures()
        rows = r if rows is None else rows
        obs = o if obs is None else obs
    return extract_causal_features(
        rows, asof=obs["asof"], observation=obs,
        is_session=nyse_calendar.is_session, market="us",
        price_basis="split_adjusted_dividend_unadjusted_close")


def test_exact_causal_depth_velocity_vol_and_episode_age():
    rows, obs = fixtures()
    out = extract(rows, obs)
    assert out["available"] is True and out["quality"] == "current"
    assert out["schema"] == "pullback_causal_features.research.v1"
    assert out["asof"] == obs["asof"]
    assert out["market"] == "us" and out["benchmark"] == "SPY"
    assert out["source_digest"] == obs["source_digest"]
    f = out["features"]
    assert f["depth_fraction"] == pytest.approx(1 - rows[-1][1]/101)
    assert f["worst_depth_fraction"] == pytest.approx(1 - min(p for _, p in rows)/101)
    assert f["rebound_fraction"] == pytest.approx(0)
    assert f["decline_5_fraction"] == pytest.approx(1 - rows[-1][1]/rows[-6][1])
    assert f["decline_10_fraction"] == pytest.approx(1 - rows[-1][1]/rows[-11][1])
    sample = [rows[i][1]/rows[i-1][1]-1 for i in range(len(rows)-20,len(rows))]
    assert f["realized_vol_20_ann"] == pytest.approx(pstdev(sample) * sqrt(252))
    assert f["observed_closes_since_onset"] == 9
    assert out["publication_authorized"] is False


def test_future_price_and_invalid_future_price_do_not_change_origin_features():
    rows, obs = fixtures()
    baseline = extract(rows, obs)
    future = nyse_calendar.session_n_forward(date.fromisoformat(obs["asof"]), 1)
    assert future is not None
    added = rows + [(future.isoformat(), -200.0), ("2099-01-01", float("nan"))]
    after = extract(added, obs)
    assert after["available"] is True
    assert after["features"] == baseline["features"]
    assert after["asof"] == baseline["asof"]


def test_missing_one_expected_session_returns_unavailable_without_forward_fill():
    rows, obs = fixtures()
    broken = rows[: -8] + rows[-7:]
    out = extract(broken, obs)
    assert not out["available"]
    assert out["quality"] == "missing_session"
    assert out["features"] is None


def test_episode_reference_is_preserved_even_after_a_rebound():
    rows, obs = fixtures()
    obs["low_close"] = obs["close"] * 0.95
    obs["peak_close"] = 110.0
    out = extract(rows, obs)
    assert out["available"]
    assert out["features"]["worst_depth_fraction"] > out["features"]["depth_fraction"]
    assert out["features"]["rebound_fraction"] == pytest.approx(1 / 0.95 - 1)


@pytest.mark.parametrize("field,value", [
    ("available", False), ("quality", "delayed"),
    ("phase", "monitoring"), ("active", False),
    ("clock", "intraday"), ("price_basis", "total_return"),
    ("market", "cn"), ("source_digest", None),
    ("asof", "2026-01-01"),
])
def test_unqualified_or_wrong_market_observations_are_not_features(field, value):
    rows, obs = fixtures()
    obs[field] = value
    out = extract(rows, obs)
    assert not out["available"]
    assert out["features"] is None


@pytest.mark.parametrize("price", [0, -1, float("nan"), float("inf"), True, "99"])
def test_invalid_trailing_price_does_not_become_a_volatility_feature(price):
    rows, obs = fixtures()
    bad = rows.copy()
    bad[-5] = (bad[-5][0], price)
    out = extract(bad, obs)
    assert not out["available"]
    assert out["quality"] == "invalid_price"


def test_conflicting_duplicate_close_fails_closed():
    rows, obs = fixtures()
    rows.insert(-1, (rows[-5][0], rows[-5][1] * 1.08))
    out = extract(rows, obs)
    assert not out["available"]
    assert out["quality"] == "conflicting_duplicate"


def test_immature_feature_window_is_unavailable():
    rows, obs = fixtures(n=15)
    out = extract(rows, obs)
    assert not out["available"]
    assert out["quality"] == "insufficient_history"
    assert out["features"] is None


@pytest.mark.parametrize("source", ["us", "cn", "", None])
def test_phase_cannot_determine_market_without_matching_identity(source):
    rows, obs = fixtures()
    obs["market"] = source
    out = extract(rows, obs)
    if source == "us":
        assert out["available"]
    else:
        assert not out["available"]


def test_output_has_no_risk_score_probability_or_position_sizing():
    out = extract()
    assert out["publication_authorized"] is False
    for forbidden in ("risk_score", "buy", "confidence", "size", "probability", "forecast"):
        assert forbidden not in out and forbidden not in (out.get("features") or {})


def test_returns_unavailable_on_close_conflict_with_canonical_observer():
    rows, obs = fixtures()
    obs["close"] = obs["close"] * 1.01
    out = extract(rows, obs)
    assert not out["available"]
    assert out["quality"] == "observation_price_mismatch"
