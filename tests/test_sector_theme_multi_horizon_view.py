"""Multi-horizon research adapter tests; no sourced market tape or deployment."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta

from engine.sector_theme_multi_horizon_view import compose_owner_multihorizon_preview
from engine.sector_theme_owner_bridge import preview_us_theme_packet
from tests.test_sector_theme_owner_bridge import fixture, quote, END


def source(horizon="5d", *, returns=(.04, .03), parent=.02, session=None):
    p = fixture()
    m = p["market"]
    m["horizon"] = horizon
    delta = timedelta(days=20 if horizon == "20d" else 5)
    if horizon == "1m":
        delta = timedelta(minutes=1)
        m["ma_basis"] = "1m_bars"
        m["session_basis"] = "rth"
    if session is not None:
        m["session_basis"] = session
    m["period_start"] = (END - delta).isoformat()
    m["benchmark"] = quote(.01, horizon=horizon)
    m["parent"] = quote(parent, horizon=horizon)
    m["member_rows"] = {
        "AAA": quote(returns[0], horizon=horizon),
        "BBB": quote(returns[1], horizon=horizon),
    }
    for item in (m["benchmark"], m["parent"], *m["member_rows"].values()):
        item["period_start"] = m["period_start"]
        item["session_basis"] = m["session_basis"]
        item["ma_basis"] = m["ma_basis"]
    out = preview_us_theme_packet(p)
    assert out["status"] == "RESEARCH_PREVIEW_ONLY", out.get("hold_reasons")
    return out


def pairs():
    return {"5d": source("5d"), "20d": source("20d")}


def held(rows, reason):
    v = compose_owner_multihorizon_preview(rows)
    assert v["status"] == "HELD", v
    assert v["reason"] == reason
    assert v["fingerprint"] is None
    assert v["customer_publication"] is False


def test_p3c_01_true_two_horizon_quantitative_projection_not_score():
    x = compose_owner_multihorizon_preview(pairs())
    assert x["status"] == "RESEARCH_PREVIEW_ONLY"
    assert x["horizons"] == ["20d", "5d"]
    assert set(x["fingerprint"]["horizons"]) == {"20d", "5d"}
    assert x["comparison_basis"]["benchmark_id"] == "SPY"
    assert x["group"]["member_ids"] == ["SEC_AAA", "SEC_BBB"]
    assert x["cross_horizon_returns_not_added_or_averaged"] is True
    assert x["owner_source_and_historical_vintage_authenticated"] is False
    assert x["forecast_or_trading_authority"] is False
    assert x["customer_publication"] is False


def test_p3c_02_short_long_parent_sign_conflict_recomputed():
    p = {
        "5d": source("5d", returns=(-.04, -.02)),
        "20d": source("20d", returns=(.20, .15)),
    }
    x = compose_owner_multihorizon_preview(p)
    assert x["status"] == "RESEARCH_PREVIEW_ONLY"
    ids = {f["id"] for f in x["fingerprint"]["facets"]}
    assert "cross_horizon_parent_rs_sign_conflict" in ids
    assert "cross_horizon_parent_rs_sign_conflict" in {
        c["tag"] for c in x["explanation"]["group_cards"]
    }
    assert x["explanation"]["predictive_or_trading_authority"] is False


def test_p3c_03_one_horizon_is_not_falsely_called_multihorizon():
    held({"5d": source("5d")}, "requires_two_distinct_horizons")
    held({}, "requires_two_distinct_horizons")
    held(None, "requires_two_distinct_horizons")


def test_p3c_04_wrong_benchmark_or_price_basis_abstains():
    p = pairs()
    p["20d"]["comparison_basis"]["benchmark_id"] = "QQQ"
    held(p, "cross_horizon_cohort_benchmark_or_clock_mismatch")
    p = pairs()
    p["20d"]["comparison_basis"]["price_basis"] = "total_return_adjusted"
    held(p, "cross_horizon_cohort_benchmark_or_clock_mismatch")


def test_p3c_05_one_overnight_read_cannot_masquerade_as_rth_cohort():
    p = pairs()
    p["20d"]["comparison_basis"]["session_basis"] = "overnight"
    held(p, "cross_horizon_cohort_benchmark_or_clock_mismatch")


def test_p3c_06_different_decision_at_is_not_same_as_known_vintage():
    p = pairs()
    p["20d"]["comparison_basis"]["decision_at"] = (
        END + timedelta(minutes=10)).isoformat()
    held(p, "frame_horizon_or_decision_mismatch")


def test_p3c_07_different_member_roster_and_cohort_refuses():
    p = pairs()
    p["20d"]["frame"]["group"]["cohort_id"] = "other-cohort"
    held(p, "cross_horizon_cohort_benchmark_or_clock_mismatch")
    p = pairs()
    p["20d"]["frame"]["universe"]["member_ids"] = ["SEC_BBB", "SEC_AAA"]
    held(p, "cross_horizon_cohort_benchmark_or_clock_mismatch")


def test_p3c_08_different_membership_known_at_refuses():
    p = pairs()
    p["20d"]["frame"]["clock"]["membership_known_at"] = (
        END - timedelta(days=6)).isoformat()
    held(p, "cross_horizon_cohort_benchmark_or_clock_mismatch")


def test_p3c_09_one_held_source_stops_whole_composite():
    p = pairs()
    p["20d"] = preview_us_theme_packet(None)
    held(p, "refused_or_unknown_owner_preview")


def test_p3c_10_malformed_issuer_mapping_is_not_a_second_vote():
    p = pairs()
    p["20d"]["issuer_by_security_id"] = {"SEC_AAA": "ISS_AAA"}
    held(p, "unqualified_issuer_population")
    p = pairs()
    p["20d"]["unique_issuer_n"] = 99
    held(p, "unqualified_issuer_population")


def test_p3c_11_predictive_authority_in_source_frame_refuses():
    p = pairs()
    p["20d"]["frame"]["authority"]["predictive_promoted"] = True
    held(p, "invalid_canonical_factor_fingerprint")
    p = pairs()
    p["20d"]["eligible_for_customer_publication"] = True
    held(p, "source_preview_claims_decision_authority")


def test_p3c_12_source_claimed_canned_text_is_recomputed():
    p = pairs()
    p["20d"]["fingerprint"]["facets"].append({
        "id": "fake_predict_tomorrow", "horizon": "20d",
    })
    p["20d"]["explanation"]["group_cards"].append({
        "tag": "fake_predict_tomorrow", "forecast_probability": .99,
    })
    out = compose_owner_multihorizon_preview(p)
    assert out["status"] == "RESEARCH_PREVIEW_ONLY"
    assert "fake_predict_tomorrow" not in repr(out)


def test_p3c_13_preview_origin_must_match_not_blend_claimed_and_synthetic():
    p = pairs()
    p["20d"]["source_origin"] = "owner_reported"
    held(p, "cross_horizon_cohort_benchmark_or_clock_mismatch")


def test_p3c_14_same_final_session_rth_minute_and_rth_daily_allowed():
    p = {"1m": source("1m"), "5d": source("5d", session="rth")}
    x = compose_owner_multihorizon_preview(p)
    assert x["status"] == "RESEARCH_PREVIEW_ONLY"
    assert x["horizons"] == ["1m", "5d"]
    assert x["per_horizon_period_start"]["1m"] != x[
        "per_horizon_period_start"]["5d"]
    assert x["comparison_basis"]["session_basis"] == "rth"


def test_p3c_15_declared_horizon_must_match_actual_source():
    p = pairs()
    p["1d"] = p.pop("20d")
    held(p, "malformed_owner_source_basis")


def test_p3c_16_no_fabricated_lagged_issuer_or_acceleration():
    x = compose_owner_multihorizon_preview(pairs())
    assert x["fingerprint"]["axes"]["rs_velocity_acceleration"]["status"] == "unmeasured"
    assert x["fingerprint"]["axes"]["cross_asset_credit"]["status"] == "unmeasured"
    assert x["fingerprint"]["horizons"]["5d"]["concentration_dispersion"][
        "issuer_hhi"]["status"] == "unmeasured"


def test_p3c_17_inputs_not_mutated_results_deterministic():
    p = pairs()
    before = deepcopy(p)
    a = compose_owner_multihorizon_preview(p)
    b = compose_owner_multihorizon_preview(p)
    assert a == b and p == before


def test_p3c_18_missing_group_or_time_source_abstains():
    p = pairs()
    p["20d"]["frame"]["group"] = None
    held(p, "malformed_frame_population")
    p = pairs()
    p["20d"]["comparison_basis"]["period_start"] = None
    held(p, "missing_or_noncausal_owner_window")


def test_p3c_19_unhashable_horizon_key_is_held_not_exception():
    p = pairs()
    p[("bad",)] = p.pop("20d")
    held(p, "malformed_horizon_or_source")
