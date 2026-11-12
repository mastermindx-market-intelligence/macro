"""S2-P3 finite session-cluster diagnostics; only synthetic proxy comparisons."""
from __future__ import annotations
from dataclasses import replace,asdict
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
import json
import pytest

from test_quote_calibration import compare
from quote_study import ExpectedSlot, TaggedComparison, StudyPolicy, assess_quote_study


DAYS=("2026-06-01","2026-06-02","2026-06-03","2026-06-04")


def slot(day="2026-06-01",security="HOUSE:A",minute=0):
    t=int(datetime.fromisoformat(day+"T09:30:00").replace(
        tzinfo=ZoneInfo("America/New_York")).timestamp())+minute*60
    return ExpectedSlot(security,day,"RTH",t,t+60)


def tagged(s,*,gap="0.1",status="COMPARABLE_PROXY_DIAGNOSTIC",
           mode="as_observed",policy="quoted_tape_v1",population="COHORT:PRE-REGISTERED"):
    row=compare()
    row=replace(row,session_id=s.session_id,security_id=s.security_id,
                phase=s.phase,start_utc_s=s.start_utc_s,end_utc_s=s.end_utc_s,
                status=status)
    if status=="COMPARABLE_PROXY_DIAGNOSTIC":
        row=replace(row,bvc_ratio=gap,quote_covered_ratio="0",
                    absolute_ratio_disagreement=gap)
    else:
        row=replace(row,absolute_ratio_disagreement=None)
    return TaggedComparison(s,row,policy,population,mode)


def study(slots=None,cells=None,**kw):
    slots=tuple(slots if slots is not None else (slot(day) for day in DAYS[:3]))
    cells=tuple(cells if cells is not None else (tagged(s) for s in slots))
    return assess_quote_study(slots,cells,cutoff_utc_s=max(s.end_utc_s for s in slots)+1
                              if slots else slot().end_utc_s+60*100,
                              policy=StudyPolicy(**kw))


def test_three_day_clusters_research_result_is_not_accuracy_or_trading_authority():
    v=study()
    assert v.status=="DESCRIPTIVE_STABILITY_AVAILABLE"
    assert v.expected_minutes==3 and v.observed_minutes==3
    assert v.comparable_minutes==3 and v.missing_minutes==0
    assert v.session_clusters_with_comparables==3
    assert v.equal_day_mean_proxy_disagreement==pytest.approx(.1)
    assert v.leave_one_day_out_low==pytest.approx(.1)
    assert v.leave_one_day_out_high==pytest.approx(.1)
    assert v.is_confidence_interval is False
    assert v.market_pilot_admitted is False and v.customer_publishable is False
    assert not any(v.authority.values())
    assert v.knowledge_class=="BAR_VS_QUOTE_PROXY_DISAGREEMENT_NOT_TAPE_TRUTH"


def test_explicit_unobserved_expected_minutes_are_missing_not_zero():
    a=study(cells=[])
    assert a.expected_minutes==3 and a.observed_minutes==0
    assert a.missing_minutes==3 and a.comparable_minutes==0
    assert a.status=="INSUFFICIENT_SESSION_CLUSTERS"
    assert a.equal_day_mean_proxy_disagreement is None
    assert a.quote_classified_share_observed is None
    assert a.per_day==(("2026-06-01",0,1,None),
                       ("2026-06-02",0,1,None),
                       ("2026-06-03",0,1,None))


def test_one_synthetically_dense_day_cannot_outvote_other_sessions():
    dates=DAYS[:3]
    slots=([slot(dates[0],minute=i) for i in range(5)]+
           [slot(dates[1]),slot(dates[2])])
    tagged_rows=([tagged(s,gap=".9") for s in slots[:5]]+
                 [tagged(slots[5],gap=".1"),tagged(slots[6],gap=".2")])
    v=study(slots,tagged_rows)
    assert v.comparable_minutes==7
    assert v.equal_day_mean_proxy_disagreement==pytest.approx(.4)
    assert v.leave_one_day_out_low==pytest.approx(.15)
    assert v.leave_one_day_out_high==pytest.approx(.55)


def test_only_two_day_clusters_withhold_stability_not_fake_two_day_confidence():
    slots=[slot(d) for d in DAYS[:2]]
    r=study(slots,[tagged(s) for s in slots])
    assert r.comparable_minutes==2
    assert r.session_clusters_with_comparables==2
    assert r.status=="INSUFFICIENT_SESSION_CLUSTERS"
    assert r.equal_day_mean_proxy_disagreement is None


def test_quote_coverage_fraction_uses_eligible_observed_print_notional():
    v=study()
    from test_quote_calibration import matched_tape
    unit=matched_tape()
    assert Decimal(v.quote_eligible_gross_observed_usd)==Decimal(unit.total_gross)*3
    assert v.quote_classified_share_observed=="1"
    assert v.quote_unknown_gross_observed_usd=="0"


def test_partial_reference_states_keep_denominator_but_null_disagreement():
    slots=[slot(d) for d in DAYS[:3]]
    rows=[tagged(slots[0]),tagged(slots[1],status="QUOTE_COVERAGE_INSUFFICIENT"),
          tagged(slots[2],status="GROSS_NOTIONAL_MISMATCH")]
    v=study(slots,rows)
    assert v.observed_minutes==3 and v.comparable_minutes==1
    assert v.not_comparable_minutes==2
    assert v.status=="INSUFFICIENT_SESSION_CLUSTERS"
    assert dict(v.status_counts)["GROSS_NOTIONAL_MISMATCH"]==1
    assert dict(v.status_counts)["QUOTE_COVERAGE_INSUFFICIENT"]==1


@pytest.mark.parametrize("state",[
    "QUOTE_COVERAGE_INSUFFICIENT","GROSS_NOTIONAL_MISMATCH",
    "BVC_DIRECTION_UNAVAILABLE","NO_ELIGIBLE_TAPE"])
def test_withheld_proxy_disagreement_must_be_null(state):
    s=slot()
    x=tagged(s,status=state)
    with pytest.raises(ValueError,match="withheld_disagreement_required"):
        study([s],[replace(x,comparison=replace(x.comparison,
                  absolute_ratio_disagreement="0.2"))])


def test_fake_compared_ratio_must_equal_absolute_declared_difference():
    s=slot()
    x=tagged(s)
    with pytest.raises(ValueError,match="disagreement_accounting"):
        study([s],[replace(x,comparison=replace(x.comparison,
                                     absolute_ratio_disagreement="1.4"))])


def test_duplicate_expected_slot_rejected():
    s=slot()
    with pytest.raises(ValueError,match="duplicate_expected"):
        study([s,s],[tagged(s)])


def test_duplicate_observation_for_same_slot_rejected():
    s=slot()
    with pytest.raises(ValueError,match="duplicate_observation"):
        study([s],[tagged(s),tagged(s)])


def test_observation_outside_owner_supplied_population_rejected():
    s=slot()
    with pytest.raises(ValueError,match="unexpected_slot"):
        study([s],[tagged(slot(security="HOUSE:B"))])


def test_mixed_comparison_policies_cannot_be_pooled():
    a,b=slot(DAYS[0]),slot(DAYS[1])
    with pytest.raises(ValueError,match="mixed_policy"):
        study([a,b],[tagged(a),tagged(b,policy="altered_quote_age")])


def test_mixed_cohorts_cannot_be_pooled():
    a,b=slot(DAYS[0]),slot(DAYS[1])
    with pytest.raises(ValueError,match="mixed_population"):
        study([a,b],[tagged(a),tagged(b,population="DIFFERENT_ROSTER")])


def test_mixed_observation_modes_rejected():
    a,b=slot(DAYS[0]),slot(DAYS[1])
    with pytest.raises(ValueError,match="mixed_mode"):
        study([a,b],[tagged(a),tagged(b,mode="corrected_history")])


def test_later_explicit_cutoff_prevents_lookahead_claims():
    s=slot()
    with pytest.raises(ValueError,match="cutoff_before"):
        assess_quote_study([s],[tagged(s)],cutoff_utc_s=s.end_utc_s-1)


def test_source_receipt_is_not_authenticated_by_declared_policy():
    a=study()
    assert a.source_receipts_verified is False
    assert a.rights_verified is False
    assert a.is_statistical_accuracy_study is False


def test_replay_and_permutation_produce_identical_results():
    all_slots=[slot(d) for d in DAYS[:3]]
    cells=[tagged(s,gap=str(Decimal(i+1)/10)) for i,s in enumerate(all_slots)]
    a=study(all_slots,cells)
    b=study(list(reversed(all_slots)),list(reversed(cells)))
    assert a==b
    assert json.loads(json.dumps(asdict(a),allow_nan=False))["expected_minutes"]==3


@pytest.mark.parametrize("threshold",[-1,0,2,True])
def test_invalid_min_session_policy_refused(threshold):
    with pytest.raises(ValueError,match="min_session_clusters"):
        study(min_session_clusters=threshold)


def test_even_full_day_replay_cannot_claim_beneficial_owner():
    result=study()
    blob=json.dumps(asdict(result))
    assert "hedge_fund_net" not in blob
    assert "institutional_buying_truth" not in blob


def test_ineligible_quote_notional_forgery_is_refused():
    s=slot()
    x=tagged(s)
    bad=replace(x,comparison=replace(x.comparison,quote_classified_gross="9999"))
    with pytest.raises(ValueError,match="quote_notional_accounting"):
        study([s],[bad])


def test_nan_or_negative_reported_notional_does_not_enter_study():
    s=slot()
    for bad in ("NaN","-1"):
        x=tagged(s)
        c=replace(x.comparison,quote_unknown_gross=bad)
        with pytest.raises(ValueError,match="unknown_invalid"):
            study([s],[replace(x,comparison=c)])


def test_misbound_security_or_phase_cannot_relabel_comparison():
    s=slot()
    x=tagged(s)
    for bad in ("HOUSE:OTHER","RTH2"):
        changed=replace(x.comparison,security_id=bad) if bad.startswith("HOUSE") else replace(x.comparison,phase=bad)
        with pytest.raises(ValueError,match="comparison_clock_identity"):
            study([s],[replace(x,comparison=changed)])


def test_comparison_that_grants_trading_authority_is_refused():
    s=slot()
    x=tagged(s)
    fake=replace(x,comparison=replace(x.comparison,authority={"may_trade":True}))
    with pytest.raises(ValueError,match="comparison_authority"):
        study([s],[fake])


def test_unknown_comparison_status_is_rejected():
    s=slot()
    x=tagged(s)
    with pytest.raises(ValueError,match="status_not_supported"):
        study([s],[replace(x,comparison=replace(x.comparison,status="LIVE_ACCURACY_PROVEN"))])


def test_ratio_disagreement_cannot_be_signed_or_out_of_bound():
    s=slot()
    for raw in ("-0.1","2.1"):
        x=tagged(s)
        wrong=replace(x.comparison,bvc_ratio=raw,absolute_ratio_disagreement=raw)
        with pytest.raises(ValueError,match="disagreement_accounting|proxy_gap_invalid"):
            study([s],[replace(x,comparison=wrong)])


def test_one_day_thousand_simulated_minutes_cannot_meet_three_day_rule():
    slots=[slot(minute=i) for i in range(30)]
    result=study(slots,[tagged(s,gap=".2") for s in slots])
    assert result.comparable_minutes==30
    assert result.session_clusters_with_comparables==1
    assert result.equal_day_mean_proxy_disagreement is None


def test_lookahead_rejected_even_if_no_current_observation():
    early=slot(DAYS[0])
    future=slot(DAYS[3])
    with pytest.raises(ValueError,match="cutoff_before"):
        assess_quote_study([early,future],[],cutoff_utc_s=early.end_utc_s+1)


def test_day_cluster_result_has_an_explicit_noninferential_stability_range():
    slots=[slot(d) for d in DAYS[:3]]
    cells=[tagged(s,gap=str(Decimal(i+1)/10)) for i,s in enumerate(slots)]
    r=study(slots,cells)
    assert r.equal_day_mean_proxy_disagreement==pytest.approx(.2)
    assert r.leave_one_day_out_low==pytest.approx(.15)
    assert r.leave_one_day_out_high==pytest.approx(.25)
    assert r.is_confidence_interval is False


def test_one_percent_comparable_minutes_cannot_expose_day_cluster_mean():
    """Three represented days are NOT sufficient when 99% of slots are missing."""
    slots=[slot(day,minute=i) for day in DAYS[:3] for i in range(100)]
    cells=[tagged(slot(day)) for day in DAYS[:3]]
    result=study(slots,cells)
    assert result.expected_minutes==300 and result.comparable_minutes==3
    assert result.session_clusters_with_comparables==3
    assert result.comparable_slot_coverage==pytest.approx(.01)
    assert result.low_coverage_sessions==DAYS[:3]
    assert result.status=="INSUFFICIENT_COMPARABLE_COVERAGE"
    assert result.equal_day_mean_proxy_disagreement is None
    assert result.leave_one_day_out_low is None
    assert result.leave_one_day_out_high is None
    assert result.quote_classified_share_observed=="1"
    assert not result.market_pilot_admitted and not result.customer_publishable


def test_at_least_eighty_percent_within_every_session_allows_descriptive_mean():
    all_slots=[slot(day,minute=i) for day in DAYS[:3] for i in range(10)]
    cells=[tagged(s) for s in all_slots if (s.start_utc_s-slot(s.session_id).start_utc_s)//60<9]
    v=study(all_slots,cells)
    assert v.comparable_minutes==27
    assert v.comparable_slot_coverage==pytest.approx(.9)
    assert v.low_coverage_sessions==()
    assert v.status=="DESCRIPTIVE_STABILITY_AVAILABLE"
    assert v.equal_day_mean_proxy_disagreement==pytest.approx(.1)


def test_one_undersampled_day_blocks_stability_even_when_three_days_present():
    all_slots=[slot(day,minute=i) for day in DAYS[:3] for i in range(10)]
    cells=[tagged(s) for s in all_slots if s.session_id!=DAYS[2] or s.start_utc_s==slot(DAYS[2]).start_utc_s]
    v=study(all_slots,cells)
    assert v.session_clusters_with_comparables==3
    assert v.comparable_slot_coverage==pytest.approx(.7)
    assert v.low_coverage_sessions==(DAYS[2],)
    assert v.status=="INSUFFICIENT_COMPARABLE_COVERAGE"
    assert v.equal_day_mean_proxy_disagreement is None


def test_unsampled_fourth_session_cannot_be_ignored_from_expected_denominator():
    all_slots=[slot(day,minute=i) for day in DAYS[:4] for i in range(10)]
    cells=[tagged(s) for s in all_slots if s.session_id in DAYS[:3]]
    v=study(all_slots,cells)
    assert v.session_clusters_with_comparables==3
    assert v.expected_session_clusters==4
    assert v.comparable_slot_coverage==pytest.approx(.75)
    assert v.low_coverage_sessions==(DAYS[3],)
    assert v.status=="INSUFFICIENT_COMPARABLE_COVERAGE"
    assert v.equal_day_mean_proxy_disagreement is None


def test_preregistered_less_strict_coverage_can_be_tested_as_sensitivity_only():
    all_slots=[slot(day,minute=i) for day in DAYS[:3] for i in range(10)]
    cells=[tagged(s) for s in all_slots if
           (s.start_utc_s-slot(s.session_id).start_utc_s)//60<6]
    strict=study(all_slots,cells)
    sensitivity=study(all_slots,cells,min_comparable_slot_coverage=.6)
    assert strict.status=="INSUFFICIENT_COMPARABLE_COVERAGE"
    assert sensitivity.status=="DESCRIPTIVE_STABILITY_AVAILABLE"
    assert sensitivity.comparable_slot_coverage==pytest.approx(.6)
    assert sensitivity.market_pilot_admitted is False
    assert sensitivity.is_confidence_interval is False
    assert sensitivity.input_digest!=strict.input_digest


@pytest.mark.parametrize("threshold",[-1,0,1.2,float("nan"),True])
def test_comparable_slot_coverage_policy_is_numeric_finite_and_positive(threshold):
    with pytest.raises(ValueError,match="comparable_slot_coverage"):
        study(min_comparable_slot_coverage=threshold)


def test_quoted_notional_coverage_is_not_calendar_minute_coverage():
    all_slots=[slot(day,minute=i) for day in DAYS[:3] for i in range(20)]
    cells=[tagged(slot(day)) for day in DAYS[:3]]
    result=study(all_slots,cells)
    assert result.quote_classified_share_observed=="1"
    assert result.comparable_slot_coverage==pytest.approx(.05)
    assert result.status=="INSUFFICIENT_COMPARABLE_COVERAGE"
    assert result.is_statistical_accuracy_study is False
