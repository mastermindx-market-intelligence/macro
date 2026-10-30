"""Hermetic counterexamples for the additive Sector/Theme Factor P1 projection.

No filesystem, market feed, clock access, production publisher or scoring gate.
All tickers, values and clocks are deliberately synthetic fixture observations.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import pytest

from engine.sector_theme_factor_intelligence import project_factor_frame

END = datetime(2026, 10, 29, 20, 0, tzinfo=timezone.utc)
DECISION = END + timedelta(minutes=5)
KNOWN = END - timedelta(days=2)


def row(
    *, ret=0.10, close=120, ma20=115, ma50=110, ma200=100,
    previous_ma50=109, period_end=END, observed_at=None,
    available_at=None, horizon="5d",
):
    return {
        "horizon": horizon,
        "period_end": period_end.isoformat(),
        "observed_at": (observed_at or (period_end + timedelta(minutes=1))).isoformat(),
        "available_at": (available_at or (period_end + timedelta(minutes=2))).isoformat(),
        "return_frac": ret,
        "close": close,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "previous_ma50": previous_ma50,
    }


def frame(*, members=("AAA", "BBB"), measurements=None, **overrides):
    kwargs = dict(
        group_id="fixture-compute", cohort_id="fixture-cohort-20261029",
        member_ids=members,
        measurements=measurements if measurements is not None
                     else {"AAA": row(), "BBB": row(ret=0.0)},
        horizon="5d", period_end=END, decision_at=DECISION,
        membership_revision="fixture-revision-1", membership_known_at=KNOWN,
        benchmark_return=0.02, parent_return=0.04,
        membership_mode="PIT_AS_KNOWN", evidence_mode="synthetic_fixture",
    )
    kwargs.update(overrides)
    return project_factor_frame(**kwargs)


def val(metric):
    assert metric["status"] == "measured", metric
    return metric["value"]


def test_p1_01_full_cohort_ew_and_relative_wealth_not_arithmetic_delta():
    f = frame(lagged_weights={"AAA": 3, "BBB": 1})
    assert val(f["measures"]["equal_weight_full_cohort_return"]) == pytest.approx(.05)
    assert val(f["measures"]["lagged_weight_full_cohort_return"]) == pytest.approx(.075)
    assert val(f["measures"]["group_rs_market"]) == pytest.approx(1.05 / 1.02 - 1)
    assert val(f["measures"]["group_rs_parent"]) == pytest.approx(1.05 / 1.04 - 1)
    assert val(f["constituents"]["AAA"]["rs_market"]) == pytest.approx(1.1 / 1.02 - 1)


def test_p1_02_missing_member_never_becomes_negative_or_full_cohort_return():
    f = frame(members=("AAA", "BBB", "CCC"), measurements={"AAA": row()})
    b = f["measures"]["positive_return_breadth"]
    assert b["k_over_n"] == pytest.approx(1.0)
    assert b["coverage"] == pytest.approx(1 / 3)
    assert b["bounds"] == pytest.approx([1 / 3, 1.0])
    assert b["bounds_kind"] == "identification_bounds_not_confidence_interval"
    assert f["universe"]["missing_by_reason"] == {"missing_observation": 2}
    assert val(f["measures"]["equal_weight_observed_sample_return"]) == pytest.approx(.1)
    assert f["measures"]["equal_weight_full_cohort_return"]["status"] == "unmeasured"
    assert f["measures"]["group_rs_market"]["status"] == "unmeasured"


def test_p1_03_all_missing_is_unmeasured_not_zero_breadth():
    f = frame(members=("AAA",), measurements={})
    b = f["measures"]["above_ma200_breadth"]
    assert b["k_over_n"] == {"status": "unmeasured", "reason": "no_measured_members"}
    assert b["coverage"] == 0.0
    assert b["bounds"] == [0.0, 1.0]
    assert f["measures"]["equal_weight_observed_sample_return"]["status"] == "unmeasured"


def test_p1_04_future_member_quote_is_refused_before_every_measurement():
    f = frame(measurements={
        "AAA": row(available_at=DECISION + timedelta(seconds=1)),
        "BBB": row(ret=-.01),
    })
    assert f["constituents"]["AAA"]["unmeasured_reason"] == "future_known"
    assert f["constituents"]["AAA"]["trend"] is None
    assert f["measures"]["uptrend_breadth"]["coverage"] == pytest.approx(.5)
    assert f["universe"]["missing_by_reason"]["future_known"] == 1


def test_p1_05_naive_row_clock_refuses_but_does_not_break_other_members():
    s = row()
    s["available_at"] = "2026-10-29T20:02:00"
    f = frame(measurements={"AAA": s, "BBB": row(ret=-.02)})
    assert f["constituents"]["AAA"]["unmeasured_reason"] == "missing_or_naive_clock"
    assert f["universe"]["measured_return_n"] == 1


def test_p1_06_mismatched_period_end_never_joins():
    old = row(period_end=END - timedelta(days=1))
    f = frame(measurements={"AAA": old, "BBB": row(ret=-.02)})
    assert f["constituents"]["AAA"]["unmeasured_reason"] == "period_end_mismatch"


def test_p1_07_wrong_horizon_never_joins():
    f = frame(measurements={"AAA": row(horizon="20d"), "BBB": row()})
    assert f["constituents"]["AAA"]["unmeasured_reason"] == "horizon_mismatch"


def test_p1_08_observation_predating_own_endpoint_is_not_pit():
    f = frame(measurements={"AAA": row(observed_at=END - timedelta(seconds=1)),
                            "BBB": row()})
    assert f["constituents"]["AAA"]["unmeasured_reason"] ==            "observation_predates_period_end"


def test_p1_09_availability_before_observation_refused():
    f = frame(measurements={
        "AAA": row(observed_at=END + timedelta(minutes=2),
                   available_at=END + timedelta(minutes=1)),
        "BBB": row(),
    })
    assert f["constituents"]["AAA"]["unmeasured_reason"] ==            "availability_predates_observation"


def test_p1_10_future_known_membership_rejected_even_if_price_old():
    with pytest.raises(ValueError, match="future market endpoint or membership"):
        frame(membership_known_at=DECISION + timedelta(days=1))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, -1.001, "0.1"])
def test_p1_11_bad_member_return_is_not_measured(bad):
    f = frame(measurements={"AAA": row(ret=bad), "BBB": row(ret=.02)})
    assert f["constituents"]["AAA"]["return_frac"]["status"] == "unmeasured"
    assert f["measures"]["positive_return_breadth"]["coverage"] == .5
    assert f["measures"]["equal_weight_full_cohort_return"]["status"] == "unmeasured"


def test_p1_12_missing_weights_or_member_returns_never_renormalize():
    valid = {"AAA": row(), "BBB": row(ret=-.05)}
    for weights, reason in [
        (None, "weights_unavailable"),
        ({"AAA": 1}, "weights_incomplete_or_extra"),
        ({"AAA": 1, "BBB": -1}, "weights_invalid"),
        ({"AAA": 0, "BBB": 0}, "weights_invalid"),
        ({"AAA": 1, "BBB": 1, "CCC": 3}, "weights_incomplete_or_extra"),
    ]:
        assert frame(measurements=valid, lagged_weights=weights)[
            "measures"]["lagged_weight_full_cohort_return"]["reason"] == reason
    f = frame(measurements={"AAA": row()}, lagged_weights={"AAA": .8, "BBB": .2})
    assert f["measures"]["lagged_weight_full_cohort_return"]["reason"] ==            "returns_incomplete"


def test_p1_13_technicals_report_up_down_and_mixed_without_scoring():
    f = frame(
        members=("AAA", "BBB", "CCC"),
        measurements={
            "AAA": row(),
            "BBB": row(ret=-.08, close=80, ma20=85, ma50=90, ma200=100,
                       previous_ma50=92),
            "CCC": row(ret=.01, close=101, ma20=110, ma50=100, ma200=95,
                       previous_ma50=99),
        },
    )
    assert [f["constituents"][sym]["trend"] for sym in ("AAA", "BBB", "CCC")] == [
        "up", "down", "mixed",
    ]
    assert f["measures"]["uptrend_breadth"]["k_over_n"] == pytest.approx(1 / 3)
    assert f["measures"]["downtrend_breadth"]["k_over_n"] == pytest.approx(1 / 3)
    assert f["measures"]["positive_return_breadth"]["k_over_n"] == pytest.approx(2 / 3)


def test_p1_14_same_member_transitions_separate_new_coverage_from_new_uptrend():
    prior_end = END - timedelta(days=7)
    prev_rows = {
        "AAA": row(period_end=prior_end, ret=-.05, close=80, ma20=85,
                   ma50=90, ma200=100, previous_ma50=92),
        "BBB": row(period_end=prior_end, ma20=None),
    }
    f = frame(
        members=("AAA", "BBB", "CCC"),
        measurements={"AAA": row(), "BBB": row(), "CCC": row()},
        previous_member_ids=("AAA", "BBB"),
        previous_measurements=prev_rows,
        previous_period_end=prior_end,
        previous_decision_at=prior_end + timedelta(minutes=5),
        previous_membership_known_at=prior_end - timedelta(days=1),
    )
    c = f["transitions"]["change"]
    assert f["transitions"]["status"] == "measured_with_endpoint_coverage"
    assert c["newly_positive_common"] == ["AAA"]
    assert c["new_coverage_positive"] == ["BBB", "CCC"]
    assert c["entrants"] == ["CCC"]
    assert c["common_cohort_after"]["k_over_n"] == pytest.approx(1.0)


def test_p1_15_unqualified_previous_endpoint_does_not_become_a_transition():
    f = frame(previous_member_ids=("AAA",), previous_measurements={"AAA": row()})
    assert f["transitions"]["status"] == "unmeasured"
    assert f["transitions"]["reason"] == "no_qualified_previous_endpoint"


def test_p1_16_previous_endpoint_must_have_its_own_earlier_knowability():
    prior_end = END - timedelta(days=7)
    with pytest.raises(ValueError, match="invalid previous endpoint"):
        frame(previous_member_ids=("AAA",),
              previous_measurements={"AAA": row(period_end=prior_end)},
              previous_period_end=prior_end,
              previous_decision_at=prior_end + timedelta(minutes=5),
              previous_membership_known_at=DECISION)


def test_p1_17_duplicate_member_ids_and_naive_top_level_clock_refused():
    with pytest.raises(ValueError, match="duplicate"):
        frame(members=("AAA", "AAA"))
    with pytest.raises(ValueError, match="aware"):
        frame(decision_at="2026-10-29T20:05:00")


def test_p1_18_noncanonical_input_extra_ticker_is_not_silent_new_membership():
    f = frame(members=("AAA",), measurements={"AAA": row(), "EXTRA": row()})
    assert list(f["constituents"]) == ["AAA"]
    assert f["universe"]["expected_n"] == 1


def test_p1_19_inputs_unchanged_order_independent_and_repeatable():
    raw = {"BBB": row(ret=.02), "AAA": row(ret=.1)}
    snapshot = copy.deepcopy(raw)
    first = frame(members=("BBB", "AAA"), measurements=raw)
    second = frame(members=("AAA", "BBB"),
                   measurements={"AAA": raw["AAA"], "BBB": raw["BBB"]})
    assert raw == snapshot
    assert first == second


def test_p1_20_never_asserts_source_rights_prediction_ranking_or_trades():
    f = frame(membership_mode="CURRENT_ROSTER",
              evidence_mode="reconstructed_price_history")
    assert f["evidence"]["source_rights_verified"] is False
    assert f["evidence"]["original_known_at_receipts_verified"] is False
    assert f["authority"]["eligible_for_customer_publication"] is False
    assert all(f["authority"][key] is False for key in
               ("predictive_promoted", "entry_or_sizing_authority",
                "ranking_authority", "alert_authority"))
    assert f["authority"]["display_only"] is True


def test_p1_21_market_benchmark_fully_lost_refuses_nonfinite_relative_wealth():
    f = frame(benchmark_return=-1.0)
    assert f["measures"]["group_rs_market"] == {
        "status": "unmeasured", "reason": "benchmark_wealth_nonpositive",
    }
    assert f["measures"]["positive_rs_market_breadth"]["coverage"] == 0.0


def test_p1_22_overlapping_members_across_groups_not_implied_disjoint():
    a = frame(members=("AAA", "BBB"))
    b = frame(group_id="fixture-semiconductors",
              members=("AAA", "CCC"),
              measurements={"AAA": row(), "CCC": row()})
    assert "AAA" in a["universe"]["member_ids"] and "AAA" in b["universe"]["member_ids"]
    assert a["group"]["overlap_policy"] == "membership_is_not_a_disjoint_partition"


def test_p1_23_mixed_return_and_technical_missingness_have_different_denominators():
    one = row(ret=None, close=120, ma50=110)
    other = row(ret=.2, close=None)
    f = frame(measurements={"AAA": one, "BBB": other})
    assert f["measures"]["positive_return_breadth"]["coverage"] == pytest.approx(.5)
    assert f["measures"]["above_ma50_breadth"]["coverage"] == pytest.approx(.5)
    assert f["measures"]["positive_return_breadth"]["k_over_n"] == 1.0
    assert f["measures"]["above_ma50_breadth"]["k_over_n"] == 1.0
