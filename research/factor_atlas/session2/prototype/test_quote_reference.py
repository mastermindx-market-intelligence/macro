"""Controlled trade/quote alignment falsifiers; no vendor tape and no aggressor truth."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import pytest

from quote_reference import (TapeTrade, TapeQuote, QuotePolicy, classify_tape)

T = 1780320600 * 1_000_000_000


def trade(identifier="t1", t=T+10_000_000_000, price="100.05",
          shares="2.5", **kw):
    base = dict(security_id="HOUSE:A", trade_id=identifier,
                session_id="2026-06-01", phase="RTH", sip_ns=t,
                available_ns=t + 50_000_000, price=price,
                decimal_size=shares, condition_state="ELIGIBLE",
                revision_ref="PRINTS_R1", rights_ref="SYNTHETIC",
                basis="unadjusted/USD", venue="LIT", correction_state="CURRENT")
    return TapeTrade(**(base | kw))


def quote(t=T+9_000_000_000, bid="100.00", ask="100.05", **kw):
    base = dict(security_id="HOUSE:A", session_id="2026-06-01",
                phase="RTH", sip_ns=t, available_ns=t+40_000_000,
                bid=bid, ask=ask, bid_size="100", ask_size="100",
                condition_state="ELIGIBLE", revision_ref="NBBO_R1",
                rights_ref="SYNTHETIC", basis="unadjusted/USD")
    return TapeQuote(**(base | kw))


def run(trades, quotes, **policy):
    return classify_tape(trades, quotes, QuotePolicy(**policy),
                         cutoff_ns=T+100_000_000_000)


def test_exact_decimal_amounts_and_unknown_accounting_bound():
    p = [
        trade("b", price="100.05", shares="2.5"),
        trade("s", t=T+20_000_000_000, price="100.00", shares="0.5"),
        trade("m", t=T+25_000_000_000, price="100.025", shares="1.25"),
    ]
    r = run(p, [quote(t=T+9_000_000_000), quote(t=T+19_000_000_000), quote(t=T+24_000_000_000)])
    assert r.total_gross == "425.15625"
    assert (r.buyer_gross,r.seller_gross,r.unknown_gross)==("250.125","50","125.03125")
    assert r.net_covered=="200.125"
    assert r.possible_full_net_min=="75.09375"
    assert r.possible_full_net_max=="325.15625"
    assert Decimal(r.buyer_gross)+Decimal(r.seller_gross)+Decimal(r.unknown_gross)==Decimal(r.total_gross)
    assert r.authority["may_publish"] is False and r.authority["may_trade"] is False


def test_quote_after_trade_cannot_classify():
    r=run([trade()], [quote(t=T+11_000_000_000)])
    assert r.details[0].state=="NO_PRECEDING_QUOTE"
    assert r.unknown_gross == r.total_gross


def test_equal_event_quote_clock_is_ambiguous_even_if_earlier_quote_exists():
    r=run([trade()], [quote(),quote(t=T+10_000_000_000,ask="100.03")])
    assert r.details[0].state=="EQUAL_TIMESTAMP_AMBIGUOUS"
    assert r.details[0].sign is None


def test_too_old_quote_does_not_reuse_stale_bidask():
    r=run([trade()], [quote(t=T+1_000_000_000)], max_age_ns=1_000_000_000)
    assert r.details[0].state=="STALE_QUOTE"
    assert r.unknown_gross==r.total_gross


@pytest.mark.parametrize("field,value",[
    ("bid","100.05"),("bid","100.07"),("bid_size","0"),
    ("ask_size","-1"),("ask","NaN")])
def test_latest_bad_quote_refuses_instead_of_rolling_back_to_older(field,value):
    good=quote(t=T+8_000_000_000)
    bad=replace(quote(t=T+9_000_000_000),**{field:value})
    r=run([trade()], [good,bad])
    assert r.details[0].state=="INVALID_QUOTE"
    assert r.details[0].sign is None


def test_future_availability_quote_is_excluded_at_cutoff():
    t=trade()
    r=classify_tape([t],[quote(available_ns=T+80_000_000_000)], QuotePolicy(),
                    cutoff_ns=T+50_000_000_000)
    assert r.details[0].state=="NO_PRECEDING_QUOTE"


def test_future_trade_does_not_change_earlier_prefix():
    first=trade()
    later=trade("future",t=T+60_000_000_000,price="-100")
    a=classify_tape([first],[quote()],QuotePolicy(),cutoff_ns=T+30_000_000_000)
    b=classify_tape([later,first],[quote()],QuotePolicy(),cutoff_ns=T+30_000_000_000)
    assert a==b


def test_quote_availability_later_than_execution_does_not_backdate_known_at():
    t=trade()
    q=quote(available_ns=T+16_000_000_000)
    r=classify_tape([t],[q],QuotePolicy(),cutoff_ns=T+20_000_000_000)
    assert r.details[0].known_at_ns==q.available_ns
    assert r.details[0].state=="QUOTE_BUY"


def test_equal_midpoint_is_explicit_unknown_by_default():
    r=run([trade(price="100.025")],[quote()])
    assert r.details[0].state=="AT_MIDPOINT_UNCLASSIFIED"
    assert r.details[0].sign is None


def test_quote_midpoint_tick_fallback_needs_prior_known_nonzero_change():
    p=[trade("a",price="100.00"),trade("b",t=T+20_000_000_000,price="100.025"),
       trade("c",t=T+30_000_000_000,price="100.025")]
    r=run(p,[quote(),quote(t=T+19_000_000_000),quote(t=T+29_000_000_000)],midpoint_policy="tick")
    assert [d.state for d in r.details]==["QUOTE_SELL","MIDPOINT_TICK_BUY","MIDPOINT_NO_TICK"]
    assert [d.sign for d in r.details]==[-1,1,None]


def test_trf_is_not_assigned_a_quote_side_by_default():
    r=run([trade(venue="TRF")],[quote()])
    assert r.details[0].state=="TRF_ALIGNMENT_UNPROVEN"
    assert r.unknown_gross==r.total_gross


def test_unresolved_or_cancelled_trade_cannot_be_honest_eligible_gross():
    p=[trade("x",condition_state="UNKNOWN"),
       trade("y",t=T+20_000_000_000,correction_state="CANCELLED"),
       trade("z",t=T+30_000_000_000)]
    r=run(p,[quote()])
    assert r.total_gross=="250.125"
    assert r.excluded_or_unqualified_gross=="500.25"
    assert r.observed_gross=="750.375"
    assert [x.state for x in r.details]==["UNQUALIFIED_PRINT","CANCELLED_PRINT","STALE_QUOTE"]


def test_duplicate_trade_id_fails_closed():
    x=trade()
    with pytest.raises(ValueError,match="duplicate_trade"):
        run([x,replace(x,price="100.00")],[quote()])


def test_duplicate_quote_at_same_clock_fails_closed():
    x=quote()
    with pytest.raises(ValueError,match="duplicate_quote"):
        run([trade()],[x,replace(x,bid="99.99")])


def test_incompatible_security_quotes_not_crossmatched():
    r=run([trade()],[quote(security_id="HOUSE:B")])
    assert r.details[0].state=="NO_PRECEDING_QUOTE"


def test_incompatible_quote_monetary_basis_fails_closed():
    with pytest.raises(ValueError,match="unproven_monetary_basis"):
        run([trade()],[quote(basis="split_adjusted/USD")])


def test_corrected_history_has_no_false_as_observed_receipt():
    r=classify_tape([trade(available_ns=None)],[quote(available_ns=None)],
                    QuotePolicy(),cutoff_ns=T+100_000_000_000,
                    mode="corrected_history")
    assert r.details[0].known_at_ns is None
    assert r.mode=="corrected_history" and r.authority["may_publish"] is False


def test_input_order_is_deterministic():
    p=[trade("a"),trade("b",t=T+20_000_000_000,price="100")]
    q=[quote(),quote(t=T+19_000_000_000)]
    assert run(p,q)==run(p[::-1],q[::-1])


@pytest.mark.parametrize("field,value",[
    ("price","NaN"),("decimal_size","0"),("decimal_size","-1"),
    ("sip_ns",True),("basis","split_adjusted/USD"),("phase","UNKNOWN"),
    ("condition_state","NOT_PROVED")
])
def test_invalid_print_contract_refuses(field,value):
    x=replace(trade(),**{field:value})
    with pytest.raises(ValueError):
        run([x],[quote()])


def test_absent_and_zero_denominator_are_distinct():
    r=run([],[])
    assert r.total_gross=="0" and r.coverage_fraction is None
    assert r.details==()


def test_derived_notional_never_claims_beneficial_owner_identity():
    r=run([trade()],[quote()])
    assert r.knowledge_class=="QUOTE_REFERENCE_INFERRED_AGGRESSOR"
    assert not hasattr(r,"hedge_fund_net_buying")


@pytest.mark.parametrize(("price","expected"),[
    ("100.00",-1),("100.01",-1),("100.025",None),
    ("100.04",1),("100.05",1),("100.06",1)])
def test_midpoint_method_agrees_with_incumbent_signing_primitive_on_ordinary_quotes(price,expected):
    from engine.flow_signing import quote_rule_sign
    raw=float(quote_rule_sign(float(price),100.00,100.05))
    assert raw==(expected or 0)
    result=run([trade(price=price)],[quote()])
    assert result.details[0].sign==expected


def test_quote_known_after_cutoff_cannot_create_a_past_signed_result():
    t=trade(available_ns=T+10_100_000_000)
    q=quote(available_ns=T+45_000_000_000)
    a=classify_tape([t],[q],QuotePolicy(),cutoff_ns=T+20_000_000_000)
    b=classify_tape([t],[],QuotePolicy(),cutoff_ns=T+20_000_000_000)
    assert a==b and a.details[0].known_at_ns==t.available_ns


def test_midpoint_tied_prior_prints_never_create_a_fake_tick():
    p=[trade("a",t=T+20_000_000_000,price="100.00"),
       trade("b",t=T+20_000_000_000,price="100.025")]
    r=run(p,[quote(t=T+19_000_000_000)],midpoint_policy="tick")
    assert r.details[1].state=="MIDPOINT_NO_TICK"


@pytest.mark.parametrize("max_age_ns",[-1,0,True,61_000_000_000])
def test_invalid_quote_age_policy_refused(max_age_ns):
    with pytest.raises(ValueError,match="invalid_quote_age"):
        run([trade()],[quote()],max_age_ns=max_age_ns)


def test_unknown_correction_occupies_diagnostic_not_eligible_denominator():
    r=run([trade(correction_state="UNRESOLVED")],[quote()])
    assert r.total_gross=="0" and r.excluded_or_unqualified_gross=="250.125"
    assert r.coverage_fraction is None and r.details[0].sign is None


def test_high_precision_decimal_notional_preserves_full_print_value():
    from decimal import localcontext
    p="100.123456789012345678901234567890"
    size="2.123456789012345678901234567890"
    with localcontext() as ctx:
        ctx.prec=256
        expected=Decimal(p)*Decimal(size)
    r=run([trade(price=p,shares=size)],[quote(bid="100.1",ask="100.2")])
    assert Decimal(r.total_gross)==expected


def test_high_precision_midpoint_must_remain_unknown_not_round_into_buy():
    low="100.00000000000000000000000000000000000000000"
    high="100.00000000000000000000000000000000000000002"
    midpoint="100.00000000000000000000000000000000000000001"
    r=run([trade(price=midpoint)],[quote(bid=low,ask=high)])
    assert r.details[0].state=="AT_MIDPOINT_UNCLASSIFIED"
    assert r.details[0].sign is None


@pytest.mark.parametrize("invalid",["1e10000000","1e-10000000"])
def test_unbounded_exponent_rejected_without_large_string(invalid):
    with pytest.raises(ValueError):
        run([trade(shares=invalid)],[quote()])
