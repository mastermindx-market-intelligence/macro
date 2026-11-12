"""BVC-versus-quote reference falsifiers on fabricated common-minute inputs."""
from dataclasses import replace
from decimal import Decimal
import pytest

from quote_calibration import ComparisonPolicy, compare_minute
import pressure as m
T = 1780320600
from test_quote_reference import trade, quote
from quote_reference import classify_tape, QuotePolicy


def tape_run(trades,quotes):
    return classify_tape(trades,quotes,QuotePolicy(),cutoff_ns=(T+300)*1_000_000_000)


def build_point(prices):
    seg=m.Segment('2026-06-01','RTH',T,T+390*60,'SYNTHETIC_CALENDAR','FULL')
    bars=[m.Bar('HOUSE:A',seg,T+k*60,T+(k+1)*60,T+(k+1)*60+2,
                p,3.,None,'unadjusted/USD','FIXTURE_REV_1','FIXTURE_RIGHTS')
          for k,p in enumerate(prices)]
    return m.bvc_series(bars,m.BVCConfig(min_returns=2),cutoff_utc_s=T+90000)[-1]


def minute_point():
    return build_point([100,101,100,100.05])


def matched_tape():
    return tape_run(
        [trade("b",t=(T+190)*1_000_000_000,price="100.05",shares="2.5"),
         trade("s",t=(T+200)*1_000_000_000,price="100.00",shares="0.5")],
        [quote(t=(T+189)*1_000_000_000),
         quote(t=(T+199)*1_000_000_000)])


def compare(point=None,tape=None,**policy):
    return compare_minute(point or minute_point(),tape or matched_tape(),
                          cutoff_ns=(T+250)*1_000_000_000,
                          policy=ComparisonPolicy(**policy))


def test_matched_minute_comparison_is_descriptive_not_accuracy_proof():
    r=compare()
    assert r.status=="COMPARABLE_PROXY_DIAGNOSTIC"
    assert r.quote_eligible_gross=="300.125"
    assert r.quote_classified_gross=="300.125"
    assert r.quote_unknown_gross=="0"
    assert r.bvc_gross_usd=="300.15"
    assert r.quote_coverage=="1"
    assert r.absolute_ratio_disagreement is not None
    assert 0<=Decimal(r.absolute_ratio_disagreement)<=2
    assert r.knowledge_class=="ESTIMATOR_COMPARISON_NOT_TAPE_TRUTH"
    assert not any(r.authority.values())


def test_quote_coverage_uses_all_eligible_prints_not_only_classified():
    t=tape_run(
        [trade("b",t=(T+190)*1_000_000_000,price="100.05",shares="2.5"),
         trade("s",t=(T+200)*1_000_000_000,price="100.00",shares="0.5")],
        [quote(t=(T+189)*1_000_000_000)])
    r=compare(tape=t)
    assert r.status=="QUOTE_COVERAGE_INSUFFICIENT"
    assert Decimal(r.quote_coverage)<Decimal("0.9")
    assert r.absolute_ratio_disagreement is None


def test_raw_close_notional_diff_is_reported_not_asserted_exact_tape_parity():
    r=compare()
    assert Decimal(r.relative_gross_gap)>0
    assert Decimal(r.relative_gross_gap)<Decimal("0.01")


def test_large_notional_discrepancy_blocks_signed_comparison():
    r=compare(tape=tape_run(
        [trade("b",t=(T+190)*1_000_000_000,shares="1")],
        [quote(t=(T+189)*1_000_000_000)]))
    assert r.status=="GROSS_NOTIONAL_MISMATCH"
    assert r.absolute_ratio_disagreement is None


def test_first_bar_policy_neutral_is_not_relabelled_tape_direction_accuracy():
    p=build_point([100])
    t=tape_run([trade(t=(T+10)*1_000_000_000,price="100.05",shares="3")],
               [quote(t=(T+9)*1_000_000_000)])
    r=compare(point=p,tape=t)
    assert r.status=="BVC_DIRECTION_UNAVAILABLE"
    assert r.absolute_ratio_disagreement is None


def test_outside_bar_prints_are_not_joined():
    r=compare(tape=tape_run(
        [trade("old",t=(T+10)*1_000_000_000,shares="3")],
        [quote(t=(T+9)*1_000_000_000)]))
    assert r.status=="NO_ELIGIBLE_TAPE"
    assert r.quote_eligible_gross=="0"


def test_same_minute_different_security_is_not_recycled():
    r=compare(tape=tape_run(
        [trade(security_id="HOUSE:OTHER",t=(T+190)*1_000_000_000,shares="3")],
        [quote(security_id="HOUSE:OTHER",t=(T+189)*1_000_000_000)]))
    assert r.status=="NO_ELIGIBLE_TAPE"


def test_later_available_tape_cannot_be_replayed_at_earlier_cutoff():
    t=tape_run([trade(t=(T+190)*1_000_000_000,
                      available_ns=(T+260)*1_000_000_000)],
               [quote(t=(T+189)*1_000_000_000)])
    with pytest.raises(ValueError,match="late_tape"):
        compare_minute(minute_point(),t,cutoff_ns=(T+250)*1_000_000_000)


def test_source_mode_mismatch_fails_closed():
    t=classify_tape([trade(available_ns=None)],[quote(available_ns=None)],
                    QuotePolicy(),cutoff_ns=(T+300)*1_000_000_000,
                    mode="corrected_history")
    with pytest.raises(ValueError,match="mode_mismatch"):
        compare(tape=t)


def test_future_bar_knowledge_does_not_pass_comparison_cutoff():
    from dataclasses import replace
    p=minute_point()
    late=replace(p.bar,available_at_utc_s=T+260)
    from dataclasses import asdict
    forged=replace(p,bar=late,input_digest=m.digest(asdict(late)))
    with pytest.raises(ValueError,match="late_bvc"):
        compare(point=forged)


def test_forged_tape_accounting_or_authority_is_rejected():
    t=matched_tape()
    with pytest.raises(ValueError,match="tape_accounting"):
        compare(tape=replace(t,buyer_gross="999999"))
    with pytest.raises(ValueError,match="authority"):
        compare(tape=replace(t,authority={"may_trade":True}))


def test_known_quote_net_interval_is_not_confidence_interval():
    t=tape_run(
        [trade("b",t=(T+190)*1_000_000_000,price="100.05",shares="2.5"),
         trade("m",t=(T+200)*1_000_000_000,price="100.025",shares="0.5")],
        [quote(t=(T+189)*1_000_000_000),
         quote(t=(T+199)*1_000_000_000)])
    r=compare(tape=t,min_quote_coverage=0.5)
    assert r.quote_unknown_gross!="0"
    assert Decimal(r.possible_quote_net_min)<Decimal(r.possible_quote_net_max)
    assert r.is_statistical_confidence_interval is False


def test_replay_determinism_and_no_trade_owner_identity_fields():
    r=compare()
    assert r==compare()
    assert not hasattr(r,"institutional_holdings_flow")


@pytest.mark.parametrize("key,value",[
    ("min_quote_coverage",0),("min_quote_coverage",1.1),
    ("max_notional_gap",-.1),("max_notional_gap",2),
])
def test_unapproved_policy_ranges_refused(key,value):
    with pytest.raises(ValueError):
        compare(**{key:value})


def test_incompatible_trade_monetary_basis_must_not_compare_as_same_population():
    # Compatible quote/print adjusted-basis *labels* are not sufficient when BVC differs.
    tr=trade("b",t=(T+190)*1_000_000_000,price="100.05",
             shares="3",basis="unadjusted/USD/action-v2")
    qt=quote(t=(T+189)*1_000_000_000,basis="unadjusted/USD/action-v2")
    t=tape_run([tr],[qt])
    with pytest.raises(ValueError,match="monetary_basis_mismatch"):
        compare(tape=t)


def test_source_rights_and_basis_are_not_discarded_by_quote_projection():
    t=matched_tape()
    assert all(d.monetary_basis=="unadjusted/USD" for d in t.details)
    assert all(d.rights_ref=="SYNTHETIC" for d in t.details)


def test_unrelated_future_prints_cannot_rewrite_earlier_minute_comparison():
    before=matched_tape()
    after=tape_run(
        [trade("b",t=(T+190)*1_000_000_000,price="100.05",shares="2.5"),
         trade("s",t=(T+200)*1_000_000_000,price="100.00",shares="0.5"),
         trade("future",t=(T+260)*1_000_000_000,price="100.01",shares="5")],
        [quote(t=(T+189)*1_000_000_000),quote(t=(T+199)*1_000_000_000),
         quote(t=(T+259)*1_000_000_000)])
    a=compare(tape=before)
    b=compare(tape=after)
    assert a==b
