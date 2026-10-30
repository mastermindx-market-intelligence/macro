"""Synthetic, no-source/no-network counterexamples for the P1a regime view.

Runs against the actual P1 projection helper; does not instantiate a new
market-data owner, HMM, publisher or entry model. No historical alpha claim.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from engine.sector_theme_factor_intelligence import project_factor_frame
from engine.sector_theme_regime_fingerprint import AXES, compose_regime_fingerprint

END = datetime(2026, 10, 29, 20, 0, tzinfo=timezone.utc)
DECISION = END + timedelta(minutes=5)


def row(
    ret=.04, *, end=END, horizon="5d", close=115, ma20=112,
    ma50=108, ma200=95, prev_ma50=106,
):
    return {
        "horizon": horizon,
        "period_end": end.isoformat(),
        "observed_at": (end + timedelta(seconds=30)).isoformat(),
        "available_at": (end + timedelta(minutes=1)).isoformat(),
        "return_frac": ret,
        "close": close, "ma20": ma20, "ma50": ma50,
        "ma200": ma200, "previous_ma50": prev_ma50,
        "ma_basis": "daily_sessions",
    }


def fact(
    *, members=("AAA", "BBB"), rows=None, horizon="5d",
    benchmark_return=0.0, parent_return=0.0, **kw,
):
    inputs = {
        "group_id": "fixture-semiconductors",
        "cohort_id": "fixture-pit-cohort-20261029",
        "member_ids": members,
        "measurements": rows if rows is not None
                        else {"AAA": row(), "BBB": row(ret=.02)},
        "horizon": horizon,
        "period_end": END,
        "decision_at": DECISION,
        "membership_revision": "fixture-revision-1",
        "membership_known_at": END - timedelta(days=5),
        "membership_mode": "PIT_AS_KNOWN",
        "evidence_mode": "synthetic_fixture",
        "benchmark_return": benchmark_return,
        "parent_return": parent_return,
    }
    inputs.update(kw)
    return project_factor_frame(**inputs)


def fp(*, rows=None, **kw):
    return compose_regime_fingerprint({"5d": fact(rows=rows, **kw)})


def facet_ids(result):
    return {f["id"] for f in result["facets"]}


def test_p1a_01_twelve_axes_and_no_alleged_forecast_or_trade_authority():
    p = fp()
    assert set(p["axes"]) == set(AXES) and len(AXES) == 12
    assert p["schema"] == "sector_theme_regime_fingerprint/v1"
    assert p["limits"]["forecast_probabilities"] == "absent"
    assert p["limits"]["numeric_state_score"] == "absent"
    assert p["authority"] == {
        "display_only": True, "predictive_promoted": False,
        "ranking_authority": False, "alert_authority": False,
        "entry_or_sizing_authority": False,
        "eligible_for_customer_publication": False,
    }


def test_p1a_02_rs_is_relative_wealth_and_not_arithmetic_difference():
    p = fp(rows={"AAA": row(ret=.10), "BBB": row(ret=.04)},
           benchmark_return=.05, parent_return=.03)
    assert p["horizons"]["5d"]["rs_market"]["value"] == pytest.approx(
        1.07 / 1.05 - 1)
    assert p["horizons"]["5d"]["rs_parent"]["value"] == pytest.approx(
        1.07 / 1.03 - 1)


def test_p1a_03_median_and_weighted_gap_need_full_member_evidence():
    p = fp(lagged_weights={"AAA": 1, "BBB": 3})
    d = p["horizons"]["5d"]["concentration_dispersion"]
    assert d["full_cohort_median_return"]["value"] == pytest.approx(.03)
    assert d["weighted_minus_equal_return"]["value"] == pytest.approx(-.005)
    assert d["issuer_hhi"]["status"] == "unmeasured"


def test_p1a_04_positive_parent_rs_with_narrowing_true_same_member_breadth():
    old_end = END - timedelta(days=7)
    p = fp(
        rows={"AAA": row(ret=-.1, close=85, ma20=90, ma50=95, ma200=100,
                          prev_ma50=96),
              "BBB": row(ret=.2)},
        previous_member_ids=("AAA", "BBB"),
        previous_measurements={"AAA": row(end=old_end),
                               "BBB": row(end=old_end)},
        previous_period_end=old_end,
        previous_decision_at=old_end + timedelta(minutes=4),
        previous_membership_known_at=old_end - timedelta(days=2),
    )
    assert p["horizons"]["5d"]["breadth_velocity_acceleration"][
        "same_member_uptrend_first_difference"]["value"] == pytest.approx(-.5)
    assert "positive_parent_rs_narrowing_same_member_breadth" in facet_ids(p)
    assert p["horizons"]["5d"]["breadth_velocity_acceleration"][
        "second_difference_acceleration"]["status"] == "unmeasured"


def test_p1a_05_negative_parent_rs_with_genuine_internal_repair():
    old_end = END - timedelta(days=7)
    p = fp(
        rows={"AAA": row(ret=-.01),
              "BBB": row(ret=-.07, close=85, ma20=90, ma50=95,
                         ma200=100, prev_ma50=96)},
        previous_member_ids=("AAA", "BBB"),
        previous_measurements={
            "AAA": row(end=old_end, close=85, ma20=90, ma50=95,
                       ma200=100, prev_ma50=96),
            "BBB": row(end=old_end, close=85, ma20=90, ma50=95,
                       ma200=100, prev_ma50=96)},
        previous_period_end=old_end,
        previous_decision_at=old_end + timedelta(minutes=4),
        previous_membership_known_at=old_end - timedelta(days=2),
    )
    assert "negative_parent_rs_internal_repair" in facet_ids(p)


def test_p1a_06_true_breadth_vs_new_coverage_not_conflated():
    old_end = END - timedelta(days=7)
    p = fp(
        rows={"AAA": row(ret=-.05, close=85, ma20=90, ma50=95,
                          ma200=100, prev_ma50=96),
              "BBB": row(ret=.08)},
        previous_member_ids=("AAA", "BBB"),
        previous_measurements={
            "AAA": row(end=old_end, close=85, ma20=90, ma50=95,
                       ma200=100, prev_ma50=96),
            "BBB": row(end=old_end, close=None),
        },
        previous_period_end=old_end,
        previous_decision_at=old_end + timedelta(minutes=4),
        previous_membership_known_at=old_end - timedelta(days=2),
    )
    v = p["horizons"]["5d"]["breadth_velocity_acceleration"]
    assert v["same_member_uptrend_first_difference"]["value"] == 0
    assert v["new_coverage_positive_n"] == 1
    assert v["composition_only"] is True
    assert "apparent_broadening_from_composition_only" in facet_ids(p)


def test_p1a_07_oversized_leader_hides_majority_negative_constituents():
    rows = {"AAA": row(ret=1.0), "BBB": row(ret=-.1),
            "CCC": row(ret=-.1)}
    p = fp(members=("AAA", "BBB", "CCC"), rows=rows)
    assert "majority_negative_participation_proven_by_bounds" in facet_ids(p)
    assert "positive_group_return_but_majority_negative" in facet_ids(p)


def test_p1a_08_missing_member_bounds_prove_broadness_when_lower_above_half():
    p = fp(members=("AAA", "BBB", "CCC", "DDD", "EEE"),
           rows={"AAA": row(ret=.01), "BBB": row(ret=.01),
                 "CCC": row(ret=.02)})
    a = p["horizons"]["5d"]["participation"]["positive_return_breadth"]
    assert a["identification_bounds"] == pytest.approx([.6, 1.0])
    assert a["coverage"] == pytest.approx(.6)
    assert "majority_positive_participation_proven_by_bounds" in facet_ids(p)
    assert p["horizons"]["5d"]["absolute_trend"]["group_return"]["status"] == "unmeasured"


def test_p1a_09_missing_member_bounds_cross_half_refuses_majority_claim():
    p = fp(members=("AAA", "BBB", "CCC", "DDD", "EEE"),
           rows={"AAA": row(ret=.01), "BBB": row(ret=.01),
                 "CCC": row(ret=-.02)})
    assert not any("majority_" in i for i in facet_ids(p))


def test_p1a_10_negative_absolute_return_can_still_outperform_market():
    p = fp(rows={"AAA": row(ret=-.04), "BBB": row(ret=-.02)},
           benchmark_return=-.08)
    assert "positive_market_rs_with_negative_absolute_return" in facet_ids(p)


def test_p1a_11_sign_conflict_across_timeframes_never_averages_5d_and_20d():
    f5 = fact(rows={"AAA": row(ret=-.03), "BBB": row(ret=-.01)},
              parent_return=0.0)
    f20 = fact(
        horizon="20d",
        rows={"AAA": row(ret=.20, horizon="20d"),
              "BBB": row(ret=.15, horizon="20d")},
        parent_return=.10,
    )
    p = compose_regime_fingerprint({"5d": f5, "20d": f20})
    assert "cross_horizon_parent_rs_sign_conflict" in facet_ids(p)
    assert p["axes"]["multiscale_coherence"]["interpretation"] == "mixed"
    assert p["axes"]["multiscale_coherence"]["positive_n"] == 1
    assert p["axes"]["multiscale_coherence"]["negative_n"] == 1


def test_p1a_12_one_horizon_does_not_prove_multiscale_coherence():
    assert fp()["axes"]["multiscale_coherence"] == {
        "status": "unmeasured", "reason": "fewer_than_two_qualified_rs_horizons",
    }


def test_p1a_13_mismatched_group_identity_is_rejected():
    a = fact()
    b = fact(horizon="20d", rows={"AAA": row(horizon="20d"),
                                  "BBB": row(horizon="20d")}, group_id="OTHER")
    with pytest.raises(ValueError, match="incompatible group"):
        compose_regime_fingerprint({"5d": a, "20d": b})


def test_p1a_14_mismatched_vintage_or_population_is_rejected():
    a = fact()
    b = fact(horizon="20d", rows={"AAA": row(horizon="20d"),
                                  "BBB": row(horizon="20d")},
             membership_revision="rev-2")
    with pytest.raises(ValueError, match="incompatible group"):
        compose_regime_fingerprint({"5d": a, "20d": b})
    b["group"]["membership_revision"] = a["group"]["membership_revision"]
    b["universe"]["member_ids"] = ["AAA"]
    b["universe"]["expected_n"] = 1
    with pytest.raises(ValueError, match="incompatible group"):
        compose_regime_fingerprint({"5d": a, "20d": b})


def test_p1a_15_mismatched_decision_time_or_horizon_is_rejected():
    a = fact()
    b = fact(horizon="20d", rows={"AAA": row(horizon="20d"),
                                  "BBB": row(horizon="20d")})
    b["clock"]["decision_at"] = (DECISION + timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError, match="incompatible group"):
        compose_regime_fingerprint({"5d": a, "20d": b})
    with pytest.raises(ValueError, match="mixed or mislabeled"):
        compose_regime_fingerprint({"20d": a})


@pytest.mark.parametrize("mutate", [
    lambda d: d["authority"].update(eligible_for_customer_publication=True),
    lambda d: d["authority"].update(ranking_authority=True),
    lambda d: d["authority"].update(predictive_promoted=True),
    lambda d: d["evidence"].update(source_rights_verified=True),
    lambda d: d["evidence"].update(original_known_at_receipts_verified=True),
])
def test_p1a_16_refuses_laundered_rights_or_authority(mutate):
    f = fact()
    mutate(f)
    with pytest.raises(ValueError, match="unqualified|source projection"):
        compose_regime_fingerprint({"5d": f})


def test_p1a_17_no_mutation_and_byte_stable_projection():
    f = fact()
    before = deepcopy(f)
    p = compose_regime_fingerprint({"5d": f})
    assert f == before
    assert p == compose_regime_fingerprint({"5d": f})
    assert not {"probability", "ranking_score", "forecast", "trade"} & set(p)


def test_p1a_18_empty_cohort_stays_unmeasured_without_false_neutral():
    p = fp(members=(), rows={})
    b = p["horizons"]["5d"]["participation"]["positive_return_breadth"]
    assert b["status"] == "unmeasured"
    assert p["horizons"]["5d"]["absolute_trend"]["group_return"]["status"] == "unmeasured"
    assert not any("majority_" in i for i in facet_ids(p))


def test_p1a_19_missing_intraday_credit_extensions_are_not_zero():
    p = fp()
    for axis in ("rs_velocity_acceleration", "extension_maturity",
                 "vol_liquidity", "cross_asset_credit"):
        assert p["axes"][axis]["status"] == "unmeasured"
        assert "reason" in p["axes"][axis]
    assert p["axes"]["evidence_quality"]["source_rights_verified"] is False


def test_p1a_20_missing_member_cannot_fabricate_dispersion():
    p = fp(members=("AAA", "BBB", "CCC"),
           rows={"AAA": row(ret=.05), "BBB": row(ret=.02)})
    assert p["horizons"]["5d"]["concentration_dispersion"][
        "full_cohort_median_return"]["status"] == "unmeasured"


def test_p1a_21_malformed_bounds_cannot_emit_false_majority_tags():
    f = fact()
    f["measures"]["positive_return_breadth"]["bounds"] = [float("nan"), 1.0]
    p = compose_regime_fingerprint({"5d": f})
    assert p["horizons"]["5d"]["participation"][
        "positive_return_breadth"]["status"] == "unmeasured"
    assert not any("majority_" in i for i in facet_ids(p))


def test_p1a_22_point_in_time_membership_cannot_postdate_endpoint():
    f = fact()
    f["clock"]["membership_known_at"] = (END + timedelta(seconds=30)).isoformat()
    with pytest.raises(ValueError, match="post-endpoint"):
        compose_regime_fingerprint({"5d": f})


def test_p1a_23_forged_expected_n_denominator_is_rejected():
    f = fact()
    f["universe"]["expected_n"] = 300
    with pytest.raises(ValueError, match="denominator"):
        compose_regime_fingerprint({"5d": f})


def test_p1a_24_positive_name_vs_parent_with_weak_group_rs():
    p = fp(
        rows={"AAA": row(ret=.05), "BBB": row(ret=-.20)},
        benchmark_return=0.0, parent_return=.02,
    )
    a = p["single_names"]["AAA"]
    assert a["horizons"]["5d"]["rs_parent"]["status"] == "measured"
    assert "name_outperforming_parent_while_group_lags_market" in {
        t["id"] for t in a["facets"]
    }
    assert a["rank_or_trading_authority"] is False


def test_p1a_25_name_above_ma50_bucking_broad_weak_group():
    p = fp(
        members=("AAA", "BBB", "CCC"),
        rows={
            "AAA": row(ret=.05),
            "BBB": row(ret=-.02, close=85, ma20=90, ma50=95,
                       ma200=100, prev_ma50=96),
            "CCC": row(ret=-.03, close=85, ma20=90, ma50=95,
                       ma200=100, prev_ma50=96),
        },
    )
    a = p["single_names"]["AAA"]
    assert a["horizons"]["5d"]["above_ma50"] is True
    assert "name_above_ma50_while_group_majority_below" in {
        t["id"] for t in a["facets"]
    }


def test_p1a_26_single_name_can_disagree_across_horizons():
    f5 = fact(rows={"AAA": row(ret=.05), "BBB": row(ret=.02)})
    f20 = fact(horizon="20d", rows={
        "AAA": row(ret=-.10, horizon="20d"),
        "BBB": row(ret=.05, horizon="20d"),
    })
    p = compose_regime_fingerprint({"5d": f5, "20d": f20})
    assert "name_parent_rs_sign_conflict_across_horizons" in {
        t["id"] for t in p["single_names"]["AAA"]["facets"]
    }
    assert p["single_names"]["AAA"]["horizons"]["20d"]["return"]["value"] == -.1


def test_p1a_27_missing_constituent_stays_named_but_unmeasured():
    p = fp(members=("AAA", "BBB", "CCC"), rows={"AAA": row(ret=.05)})
    for name in ("BBB", "CCC"):
        assert p["single_names"][name]["horizons"]["5d"]["rs_parent"][
            "status"] == "unmeasured"
        assert p["single_names"][name]["facets"] == []


def test_p1a_28_per_name_source_time_and_ma_basis_are_retained():
    p = fp()
    assert p["single_names"]["AAA"]["horizons"]["5d"]["period_end"] == END.isoformat()
    assert p["single_names"]["AAA"]["horizons"]["5d"]["ma_basis"] == "daily_sessions"
    assert p["single_names"]["AAA"]["horizons"]["5d"]["above_ma200"] is True
