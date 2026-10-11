"""S2-P6 scientific gate: fabricated, *owner-unverified* paired OOS forecasts."""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import math
import pytest

from pressure_oos import (EvaluationPlan, EvaluationSlot, PairedForecast,
                          evaluate_oos)

ET=ZoneInfo("America/New_York")
def ts(day:date,hour=10):
    return int(datetime(day.year,day.month,day.day,hour,0,tzinfo=ET).timestamp())
DAYS=tuple(date(2026,2,2)+timedelta(days=n) for n in range(29)
           if (date(2026,2,2)+timedelta(days=n)).weekday()<5)[:20]
assert len(DAYS)==20
DEVELOPMENT_END=ts(date(2026,1,30))
START=ts(date(2026,2,2),9)
END=ts(date(2026,3,6),16)

def plan(**change):
    return EvaluationPlan(**(dict(
      experiment_ref="SESSION2_SYNTHETIC_OOS",
      factor_ref="HOUSE_FACTOR:A",
      population_ref="HOUSE_PIT_PROPOSED",
      roster_ref="ROSTER:OLD:TEST",
      membership_mode="point_in_time",
      target_ref="NEXT_30M_RESIDUAL_RETURN_BPS",
      horizon_seconds=1800,
      development_end_utc_s=DEVELOPMENT_END,
      holdout_start_utc_s=START,
      holdout_end_utc_s=END,
      embargo_seconds=1800,
      minimum_days=20,
      minimum_outcome_coverage=.8,
      control_model_ref="PRE-FROZEN_FLEXIBLE_PRICE_VOL_TURNOVER",
      pressure_model_ref="PRE-FROZEN_PLUS_BVC",
      feature_basis_ref="CANONICAL_CONTEXT_V1") | change))

def slot(day=DAYS[0],minute=0):
    return EvaluationSlot("HOUSE_FACTOR:A",day.isoformat(),ts(day)+minute*60)

def row(s:EvaluationSlot,control=0.,candidate=1.,actual=1.,**change):
    t=s.decision_utc_s
    base=dict(
      slot=s,
      factor_membership_ref="ROSTER:OLD:TEST",
      population_ref="HOUSE_PIT_PROPOSED",
      membership_mode="point_in_time",
      feature_known_at_utc_s=t-3,
      control_known_at_utc_s=t-2,
      pressure_known_at_utc_s=t-2,
      realized_end_utc_s=t+1800,
      realized_known_at_utc_s=t+1801,
      control_prediction_bps=control,
      pressure_prediction_bps=candidate,
      realized_residual_return_bps=actual,
      observed_basis_ref="CANONICAL_CONTEXT_V1",
      outcome_source_ref="SYNTHETIC_OUTCOME_FIXTURE",
      pressure_source_ref="SYNTHETIC_PRICE_VOLUME_FIXTURE",
      mode="as_observed")
    return PairedForecast(**(base|change))

def sample():
    slots=tuple(slot(d) for d in DAYS)
    return slots,tuple(row(s) for s in slots)

def study(slots=None,rows=None,**kwargs):
    base_s,base_r=sample()
    return evaluate_oos(plan(),base_s if slots is None else slots,
                        base_r if rows is None else rows,
                        evaluation_at_utc_s=END+4000,**kwargs)


def test_twenty_holdout_day_paired_loss_is_descriptive_never_alpha_claim():
    v=study()
    assert v.status=="DESCRIPTIVE_OOS_COMPARISON"
    assert v.expected_slots==20 and v.matured_matched_slots==20
    assert v.unavailable_slots==0 and v.outcome_coverage==1.
    assert v.day_clusters==20
    assert v.control_mse_bps2==1.
    assert v.pressure_mse_bps2==0.
    assert v.day_equal_loss_improvement_bps2==1.
    assert v.relative_mse_improvement==1.
    assert v.leave_one_day_out_low==pytest.approx(1.)
    assert v.leave_one_day_out_high==pytest.approx(1.)
    assert v.is_confidence_interval is False
    assert not v.real_market_data_admitted and not v.source_rights_proven
    assert v.customer_publishable is False
    assert not any(flag for name,flag in v.authority)
    assert v.knowledge_class=="FORECAST_PAIR_DIAGNOSTIC_NOT_TRADING_ALPHA"


def test_incomplete_population_retains_denominator_not_zero_filled_outcome():
    slots,rows=sample()
    v=study(slots=slots,rows=rows[:-4])
    assert v.status=="INSUFFICIENT_HOLDOUT_SESSIONS"
    assert v.expected_slots==20 and v.matured_matched_slots==16
    assert v.unavailable_slots==4
    assert v.control_mse_bps2 is None
    assert v.pressure_mse_bps2 is None
    assert v.day_equal_loss_improvement_bps2 is None


def test_zero_control_error_does_not_invent_infinite_relative_improvement():
    s,r=sample()
    rows=tuple(row(x,control=1.,candidate=0.,actual=1.) for x in s)
    v=study(slots=s,rows=rows)
    assert v.control_mse_bps2==0 and v.pressure_mse_bps2==1.
    assert v.relative_mse_improvement is None
    assert v.day_equal_loss_improvement_bps2==-1.


def test_negative_incremental_effect_is_not_suppressed():
    s,r=sample()
    worse=tuple(row(x,control=1.,candidate=0.,actual=1.) for x in s)
    v=study(slots=s,rows=worse)
    assert v.day_equal_loss_improvement_bps2<0
    assert v.status=="DESCRIPTIVE_OOS_COMPARISON"


def test_many_minutes_one_day_cannot_meet_minimum_day_clusters():
    s=(tuple(slot(DAYS[0],i) for i in range(20))+
       tuple(slot(d) for d in DAYS[1:3]))
    v=study(slots=s,rows=[row(x) for x in s])
    assert v.matured_matched_slots==22 and v.day_clusters==3
    assert v.status=="INSUFFICIENT_HOLDOUT_SESSIONS"


def test_later_outcome_not_yet_known_is_withheld_at_first_evaluation():
    s,r=sample()
    late=replace(r[0],realized_known_at_utc_s=END+8000)
    v=study(slots=s,rows=(late,*r[1:]))
    assert v.matured_matched_slots==19
    assert v.unavailable_slots==1
    assert v.status=="INSUFFICIENT_HOLDOUT_SESSIONS"


def test_outcome_maturity_time_cannot_precede_actual_label_end():
    s,r=sample()
    with pytest.raises(ValueError,match="outcome_before_event"):
        study(slots=s,rows=(replace(r[0],realized_known_at_utc_s=s[0].decision_utc_s+15),*r[1:]))


@pytest.mark.parametrize("clock",["feature_known_at_utc_s",
                                  "control_known_at_utc_s",
                                  "pressure_known_at_utc_s"])
def test_predictor_features_known_after_decision_refused(clock):
    s,r=sample()
    forged=replace(r[0],**{clock:s[0].decision_utc_s+1})
    with pytest.raises(ValueError,match="forecast_lookahead"):
        study(slots=s,rows=(forged,*r[1:]))


def test_holdout_embargo_must_cover_full_target_horizon():
    s,r=sample()
    with pytest.raises(ValueError,match="embargo"):
        evaluate_oos(plan(embargo_seconds=60),s,r,evaluation_at_utc_s=END+4000)


def test_training_end_just_before_holdout_without_gap_fails_closed():
    s,r=sample()
    with pytest.raises(ValueError,match="embargo"):
        evaluate_oos(plan(development_end_utc_s=START-100),s,r,
                     evaluation_at_utc_s=END+4000)


def test_outcome_end_must_be_exact_registered_30_min_horizon():
    s,r=sample()
    wrong=replace(r[0],realized_end_utc_s=r[0].realized_end_utc_s+60,
                  realized_known_at_utc_s=r[0].realized_known_at_utc_s+60)
    with pytest.raises(ValueError,match="horizon_mismatch"):
        study(slots=s,rows=(wrong,*r[1:]))


def test_control_family_identity_is_required_and_must_be_distinct():
    s,r=sample()
    with pytest.raises(ValueError,match="model_identity"):
        evaluate_oos(plan(control_model_ref="PRE-FROZEN_PLUS_BVC"),s,r,evaluation_at_utc_s=END+4000)


def test_same_day_duplicate_forecast_for_same_factor_minute_refused():
    s,r=sample()
    with pytest.raises(ValueError,match="duplicate_observation"):
        study(slots=s,rows=(*r,r[0]))


def test_duplicate_expected_slots_refused():
    s,r=sample()
    with pytest.raises(ValueError,match="duplicate_expected"):
        study(slots=(*s,s[0]),rows=r)


def test_outside_holdout_window_refused_not_silently_added():
    s,r=sample()
    prior=slot(date(2026,1,30))
    with pytest.raises(ValueError,match="outside_holdout"):
        study(slots=(*s,prior),rows=r)


def test_unexpected_forecast_source_slot_refused():
    s,r=sample()
    with pytest.raises(ValueError,match="unexpected_slot"):
        study(slots=s,rows=(*r,row(slot(DAYS[0],1))))


def test_current_cohort_in_pit_forecast_experiment_refused():
    s,r=sample()
    with pytest.raises(ValueError,match="membership_mode"):
        study(slots=s,rows=(replace(r[0],membership_mode="current_cohort"),*r[1:]))


def test_factor_membership_ref_cannot_change_without_reregistered_study():
    s,r=sample()
    with pytest.raises(ValueError,match="roster_mismatch"):
        study(slots=s,rows=(replace(r[0],factor_membership_ref="DIFFERENT_ROSTER"),*r[1:]))


def test_source_basis_mismatch_cannot_enter_same_mse_denominator():
    s,r=sample()
    with pytest.raises(ValueError,match="basis_mismatch"):
        study(slots=s,rows=(replace(r[0],observed_basis_ref="split_adjusted/DIVERGENT"),*r[1:]))


def test_different_factor_prediction_cannot_be_injected():
    s,r=sample()
    wrong=replace(r[0],slot=replace(r[0].slot,factor_ref="OTHER_FACTOR"))
    with pytest.raises(ValueError,match="unexpected_slot"):
        study(slots=s,rows=(wrong,*r[1:]))


@pytest.mark.parametrize("field",["control_prediction_bps",
                                  "pressure_prediction_bps",
                                  "realized_residual_return_bps"])
def test_nan_infinite_or_boolean_predictions_fail_closed(field):
    s,r=sample()
    for bad in (float("nan"),float("inf"),True):
        with pytest.raises(ValueError,match="finite"):
            study(slots=s,rows=(replace(r[0],**{field:bad}),*r[1:]))


def test_permutation_and_future_outside_population_do_not_change_result():
    s,r=sample()
    a=study(slots=s,rows=r)
    b=study(slots=tuple(reversed(s)),rows=tuple(reversed(r)))
    assert a==b
    after=slot(date(2026,3,10))
    with pytest.raises(ValueError,match="unexpected_slot"):
        study(slots=s,rows=(*r,row(after)))
    assert json.loads(json.dumps(asdict(a),allow_nan=False))["source_rights_proven"] is False


def test_date_boundary_et_contract_and_unknown_phase_refuse():
    s,r=sample()
    bad=replace(s[0],session_id="2026-02-03")
    with pytest.raises(ValueError,match="session_clock"):
        study(slots=(bad,*s[1:]),rows=r)


def test_undercovered_holdout_not_declared_informative_even_with_20_days():
    s,r=sample()
    a=study(slots=s,rows=r,min_day_coverage_override=None)
    assert a.status=="DESCRIPTIVE_OOS_COMPARISON"
    s2=tuple([slot(d) for d in DAYS]+[slot(d,minute=1) for d in DAYS])
    r2=tuple(row(slot(d)) for d in DAYS)
    v=study(slots=s2,rows=r2)
    assert v.day_clusters==20 and v.outcome_coverage==.5
    assert v.status=="INSUFFICIENT_OUTCOME_COVERAGE"
    assert v.day_equal_loss_improvement_bps2 is None


def test_results_never_claim_signing_accuracy_or_beneficial_owner():
    v=study()
    payload=json.dumps(asdict(v))
    assert "hedge_fund" not in payload and "trade_aggressor_truth" not in payload
    assert v.is_statistical_accuracy_study is False


def test_forecast_receipt_cannot_precede_latest_feature_it_uses():
    s,r=sample()
    altered=replace(r[0],pressure_known_at_utc_s=r[0].feature_known_at_utc_s-1)
    with pytest.raises(ValueError,match="forecast_precedes_feature"):
        study(slots=s,rows=(altered,*r[1:]))


def test_label_missing_with_claimed_available_timestamp_is_contradictory():
    s,r=sample()
    forged=replace(r[0],realized_residual_return_bps=None)
    with pytest.raises(ValueError,match="outcome_receipt_without_label"):
        study(slots=s,rows=(forged,*r[1:]))


def test_missing_label_without_receipt_is_explicitly_unavailable():
    s,r=sample()
    absent=replace(r[0],realized_residual_return_bps=None,realized_known_at_utc_s=None)
    v=study(slots=s,rows=(absent,*r[1:]))
    assert v.matured_matched_slots==19 and v.unavailable_slots==1
    assert v.status=="INSUFFICIENT_HOLDOUT_SESSIONS"


def test_later_unavailable_outcome_values_cannot_change_earlier_digest():
    s,r=sample()
    t=r[0]
    a=replace(t,realized_known_at_utc_s=END+5000,realized_residual_return_bps=10.)
    b=replace(t,realized_known_at_utc_s=END+7000,realized_residual_return_bps=-5.)
    x=study(slots=s,rows=(a,*r[1:]))
    y=study(slots=s,rows=(b,*r[1:]))
    assert x==y and x.input_digest==y.input_digest


def test_equal_zero_prediction_losses_are_finite_with_null_relative_ratio():
    s,r=sample()
    zeros=tuple(row(x,control=0.,candidate=0.,actual=0.) for x in s)
    v=study(slots=s,rows=zeros)
    assert v.control_mse_bps2==0 and v.pressure_mse_bps2==0
    assert v.day_equal_loss_improvement_bps2==0
    assert v.relative_mse_improvement is None


def test_winning_on_19_days_is_not_masked_by_one_overrepresented_day():
    s,r=sample()
    more=tuple(slot(DAYS[0],minute=i) for i in range(1,20))
    all_expected=(*s,*more)
    all_rows=[row(x,control=0.,candidate=1.,actual=1.) for x in s[1:]]
    all_rows.extend(row(x,control=0.,candidate=10.,actual=1.) for x in (s[0],*more))
    v=study(slots=all_expected,rows=all_rows)
    assert v.matured_matched_slots==39
    assert v.day_clusters==20
    assert v.day_equal_loss_improvement_bps2==pytest.approx((19-80)/20)
    assert v.control_mse_bps2==pytest.approx(1.)


def test_nineteen_day_plan_cannot_relax_holdout_after_looking_at_results():
    s,r=sample()
    with pytest.raises(ValueError,match="minimum_holdout_days"):
        evaluate_oos(plan(minimum_days=19),s,r,evaluation_at_utc_s=END+4000)


def test_primary_horizon_cannot_be_shortened_to_favor_an_outcome():
    s,r=sample()
    with pytest.raises(ValueError,match="30min"):
        evaluate_oos(plan(horizon_seconds=600),s,r,evaluation_at_utc_s=END+4000)


@pytest.mark.parametrize("clock",["feature_known_at_utc_s",
                                  "control_known_at_utc_s",
                                  "pressure_known_at_utc_s"])
def test_nonpositive_first_observation_receipt_rejected(clock):
    s,r=sample()
    with pytest.raises(ValueError,match="clock_positive"):
        study(slots=s,rows=(replace(r[0],**{clock:-1}),*r[1:]))


def test_forecast_labels_must_be_owner_verifiable_and_not_inferentially_promoted():
    v=study()
    assert v.real_market_data_admitted is False
    assert v.source_rights_proven is False
    assert v.is_statistical_accuracy_study is False
    assert v.knowledge_class=="FORECAST_PAIR_DIAGNOSTIC_NOT_TRADING_ALPHA"


def test_one_thin_day_with_fifteen_percent_missing_aggregate_returns_no_oos_loss():
    """Global 95.5% label coverage cannot hide one 10%-observed session."""
    expected=tuple(slot(day,minute=i) for day in DAYS for i in range(10))
    observed=tuple(row(s) for s in expected if
       s.session_id!=DAYS[-1].isoformat() or s.decision_utc_s==slot(DAYS[-1]).decision_utc_s)
    result=study(slots=expected,rows=observed)
    assert result.expected_slots==200 and result.matured_matched_slots==191
    assert result.outcome_coverage==pytest.approx(.955)
    assert result.day_clusters==20
    assert result.low_coverage_sessions==(DAYS[-1].isoformat(),)
    assert result.status=="INSUFFICIENT_DAY_OUTCOME_COVERAGE"
    assert result.control_mse_bps2 is None
    assert result.pressure_mse_bps2 is None
    assert result.day_equal_loss_improvement_bps2 is None
    assert not any(flag for _,flag in result.authority)


def test_ninety_percent_labels_in_every_day_retains_descriptive_oos():
    expected=tuple(slot(day,minute=i) for day in DAYS for i in range(10))
    observed=tuple(row(s) for s in expected if
       (s.decision_utc_s-slot(s.session_id and date.fromisoformat(s.session_id)).decision_utc_s)//60<9)
    result=study(slots=expected,rows=observed)
    assert result.matured_matched_slots==180
    assert result.low_coverage_sessions==()
    assert result.status=="DESCRIPTIVE_OOS_COMPARISON"
    assert result.day_equal_loss_improvement_bps2==pytest.approx(1.)


def test_exactly_eighty_percent_per_day_is_eligible_but_not_confident():
    expected=tuple(slot(day,minute=i) for day in DAYS for i in range(10))
    observed=tuple(row(s) for s in expected if
       (s.decision_utc_s-slot(date.fromisoformat(s.session_id)).decision_utc_s)//60<8)
    result=study(slots=expected,rows=observed)
    assert result.outcome_coverage==pytest.approx(.8)
    assert result.low_coverage_sessions==()
    assert result.status=="DESCRIPTIVE_OOS_COMPARISON"
    assert result.is_confidence_interval is False
    assert result.is_statistical_accuracy_study is False


def test_sparse_ninety_nine_percent_global_but_one_undercovered_day_refuses():
    expected=tuple(slot(day,minute=i) for day in DAYS for i in range(10))
    observed=tuple(row(s) for s in expected if
      s.session_id!=DAYS[-1].isoformat() or
      (s.decision_utc_s-slot(DAYS[-1]).decision_utc_s)//60<7)
    r=study(slots=expected,rows=observed)
    assert r.outcome_coverage==pytest.approx(.985)
    assert r.day_clusters==20
    assert r.low_coverage_sessions==(DAYS[-1].isoformat(),)
    assert r.status=="INSUFFICIENT_DAY_OUTCOME_COVERAGE"
    assert r.leave_one_day_out_high is None


def test_insufficient_day_label_fractions_not_equivalent_to_no_day_labels():
    expected=tuple(slot(day,minute=i) for day in DAYS for i in range(10))
    observed=tuple(row(s) for s in expected if
      s.session_id!=DAYS[-1].isoformat() or
      s.decision_utc_s==slot(DAYS[-1]).decision_utc_s)
    result=study(slots=expected,rows=observed)
    assert result.day_clusters==20
    assert result.low_coverage_sessions!=(DAYS[:1][0].isoformat(),)
    assert result.per_day[-1].expected_slots==10
    assert result.per_day[-1].matured_slots==1
    assert result.input_digest


@pytest.mark.parametrize("unavailable_future_label",[
    float("nan"),float("inf"),float("-inf"),10**100,"invalid_future_label",True,
])
def test_future_unavailable_label_payload_cannot_poison_historical_oos_prefix(unavailable_future_label):
    """A future label's unreceived value is outside the earlier information set.

    At the earlier evaluation cutoff even an invalid later-vintage value must
    not change the no-label result. Once learned, the value must be validated.
    """
    slots,rows=sample()
    later_clock=END+8000
    clean=replace(rows[0],realized_known_at_utc_s=later_clock,
                  realized_residual_return_bps=10.)
    future_bad=replace(clean,realized_residual_return_bps=unavailable_future_label)
    earlier=study(slots=slots,rows=(clean,*rows[1:]))
    candidate=study(slots=slots,rows=(future_bad,*rows[1:]))
    assert earlier==candidate
    assert candidate.status=="INSUFFICIENT_HOLDOUT_SESSIONS"
    assert candidate.matured_matched_slots==19
    assert candidate.input_digest==earlier.input_digest
    with pytest.raises(ValueError,match="finite|outside_research_bounds"):
        evaluate_oos(plan(),slots,(future_bad,*rows[1:]),
                     evaluation_at_utc_s=later_clock+1)


def test_preavailability_future_label_changes_do_not_change_prior_day_loss():
    slots,rows=sample()
    when=END+8000
    original=replace(rows[0],realized_known_at_utc_s=when,
                     realized_residual_return_bps=100.)
    corrected=replace(original,realized_residual_return_bps=-200.)
    a=study(slots=slots,rows=(original,*rows[1:]))
    b=study(slots=slots,rows=(corrected,*rows[1:]))
    assert a==b
    assert a.control_mse_bps2 is None and b.control_mse_bps2 is None
