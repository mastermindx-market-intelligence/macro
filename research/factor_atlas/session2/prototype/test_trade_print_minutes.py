"""Synthetic only: reconstruct candidate trade-print minutes without source admission."""
from dataclasses import replace
from decimal import Decimal

import pytest
import pressure as m
import source_preflight as sp
from quote_reference import TapeTrade
from trade_print_minutes import PrintSelection, reconstruct_print_minutes

T=1780320600
NS=1_000_000_000
NAMES=("AAPL","MSFT","NVDA","SPY")
SEG=m.Segment("2026-06-01","RTH",T,T+120,"CAL:2026-06-01:RTH:UNVERIFIED","FULL")
SCOPE=sp.IntakeScope(NAMES,(SEG,),(T+180)*NS)


def print_trade(id="t1", *, offset_s=10, price="100.01", size="0.25", **kwargs):
    event=(T+offset_s)*NS
    fields=dict(
        security_id="AAPL",trade_id=id,session_id="2026-06-01",
        phase="RTH",sip_ns=event,available_ns=event+10_000,
        price=price,decimal_size=size,condition_state="ELIGIBLE",
        revision_ref="SYNTHETIC:PRINTS:V1",rights_ref="SYNTHETIC_ONLY",
        basis="unadjusted/USD",venue="LIT",correction_state="CURRENT")
    return TapeTrade(**(fields|kwargs))


def chosen(*trades):
    return tuple(PrintSelection(t,True,True) for t in trades)


def assess(records=None, **kwargs):
    return reconstruct_print_minutes(
        chosen(print_trade(),print_trade("t2",offset_s=20,price="100.03",size="0.75"))
        if records is None else records,
        scope=SCOPE, **kwargs)


def test_fractional_print_size_and_exact_money_without_float_or_integer_rounding():
    x=assess()
    assert x.status=="SYNTHETIC_PRINT_SAMPLE_NOT_ADMITTED"
    assert x.observed_candidate_cells==1
    assert x.matched_print_cells==1 and x.only_withheld_cells==0
    assert x.expected_cells==8
    assert x.absent_candidate_cells==7
    assert x.explicit_no_trade_cells==0
    assert len(x.minutes)==1
    z=x.minutes[0]
    assert z.security_id=="AAPL" and z.start_utc_s==T and z.end_utc_s==T+60
    assert z.candidate_share_volume=="1"
    assert z.candidate_trade_gross_usd=="100.025"
    assert z.candidate_open=="100.01" and z.candidate_high=="100.03"
    assert z.candidate_low=="100.01" and z.candidate_close=="100.03"
    assert z.prints_selected==2 and z.prints_withheld==0
    assert z.prices_are_owner_admitted is False
    assert z.consolidated_population_proven is False
    assert x.market_pilot_admitted is False and x.customer_publishable is False
    assert not any(flag for _,flag in x.authority)


def test_missing_slot_does_not_turn_into_zero_and_empty_input_is_not_zero_activity():
    x=assess(())
    assert x.minutes==()
    assert x.expected_cells==8 and x.absent_candidate_cells==8
    assert x.explicit_no_trade_cells==0
    assert x.status=="SYNTHETIC_PRINT_SAMPLE_NOT_ADMITTED"
    assert x.market_pilot_admitted is False


def test_later_append_and_late_capture_do_not_rewrite_prior_as_observed_sample():
    now=replace(SCOPE,cutoff_utc_ns=(T+90)*NS)
    t=print_trade()
    first=reconstruct_print_minutes(chosen(t),scope=now)
    append=reconstruct_print_minutes(chosen(
        t,
        print_trade("after_window",offset_s=95,price="-1"),
        print_trade("late_receipt",offset_s=30,available_ns=(T+100)*NS)),
        scope=now)
    assert first==append
    assert first.minutes[0].latest_known_at_ns==t.available_ns


def test_retrospective_mode_does_not_invent_original_availability():
    t=print_trade(available_ns=None)
    x=assess(chosen(t),mode="corrected_history")
    assert x.minutes[0].latest_known_at_ns is None
    assert x.mode=="corrected_history"
    assert not x.pit_backtest_admitted
    with pytest.raises(ValueError,match="first_known_unavailable"):
        assess(chosen(t))


def test_missing_original_sale_condition_selection_withholds_entire_print():
    t=print_trade()
    x=assess((PrintSelection(t,None,True),))
    assert len(x.minutes)==1
    assert x.minutes[0].candidate_share_volume is None
    assert x.minutes[0].candidate_trade_gross_usd is None
    assert x.minutes[0].prints_withheld==1
    assert x.minutes[0].prints_selected==0
    assert x.matched_print_cells==0 and x.only_withheld_cells==1
    assert "OWNER_ELIGIBILITY_UNKNOWN" in x.minutes[0].refusals


@pytest.mark.parametrize("bad",[
    {"condition_state":"UNKNOWN"},
    {"correction_state":"CANCELLED"},
    {"correction_state":"UNRESOLVED"},
    {"venue":"TRF"}])
def test_unknown_conditions_corrections_or_trf_never_mint_eligible_trade_bar(bad):
    result=assess(chosen(print_trade(**bad)))
    assert result.minutes[0].prints_selected==0
    assert result.minutes[0].prints_withheld==1
    assert result.minutes[0].candidate_share_volume is None
    assert result.market_pilot_admitted is False


def test_owner_false_flags_remain_distinct_from_missing_flags():
    t=print_trade()
    result=assess((PrintSelection(t,False,True),))
    assert result.minutes[0].prints_selected==0
    assert "PRINT_NOT_IN_MATCHED_OHLC_VOLUME_POPULATION" in result.minutes[0].refusals


@pytest.mark.parametrize("flag",["true",1,[],{}])
def test_eligibility_flags_must_be_actual_bools_or_none(flag):
    with pytest.raises(ValueError,match="eligibility_boolean_required"):
        assess((PrintSelection(print_trade(),flag,True),))


def test_order_invariance_under_exact_event_clocks():
    a=chosen(print_trade(),print_trade("t2",offset_s=20,price="100.03",size="0.75"))
    assert assess(a)==assess(tuple(reversed(a)))


def test_identical_sip_nanoseconds_with_different_prices_withhold_open_close():
    t1=print_trade("a",offset_s=10,price="100.01")
    t2=print_trade("b",offset_s=10,price="100.03")
    x=assess(chosen(t1,t2))
    z=x.minutes[0]
    assert z.candidate_open is None and z.candidate_close is None
    assert z.candidate_high=="100.03" and z.candidate_low=="100.01"
    assert z.prints_selected==2
    assert "EVENT_ORDER_NOT_PROVEN" in z.refusals


def test_duplicate_trade_id_requires_original_revision_selector():
    with pytest.raises(ValueError,match="duplicate_trade_needs_original_selector"):
        assess(chosen(print_trade(),print_trade(price="100.04")))


def test_source_venue_and_date_claims_cannot_be_self_authenticated():
    wrong=print_trade(session_id="2026-06-02")
    with pytest.raises(ValueError,match="event_session_mismatch"):
        assess(chosen(wrong))
    out=print_trade(offset_s=-10)
    with pytest.raises(ValueError,match="outside_owner_calendar"):
        assess(chosen(out))


def test_unknown_source_never_exports_price_levels_or_claims_capability():
    x=reconstruct_print_minutes(chosen(print_trade()),scope=SCOPE,input_class="OWNER_UNVERIFIED")
    assert x.minutes==() and x.observed_candidate_cells==0
    assert x.status=="SOURCE_UNVERIFIED_NOT_REDUCED"
    assert x.customer_publishable is False and x.market_pilot_admitted is False


def test_nonqualified_source_labels_cannot_grant_trade_or_research_accuracy():
    assert assess(chosen(print_trade(rights_ref="claimed_business_license"))).market_pilot_admitted is False
    assert assess(chosen(print_trade(revision_ref="claimed_latest"))).pit_backtest_admitted is False


def test_actual_synthetic_print_gross_is_not_bvc_close_times_volume_proxy():
    # A signed BVC result has a different estimand from executed print notional.
    # Do not silently relabel the two when a qualified feed eventually arrives.
    z=assess().minutes[0]
    exact=Decimal("100.01")*Decimal("0.25")+Decimal("100.03")*Decimal("0.75")
    proxy=Decimal(z.candidate_close)*Decimal(z.candidate_share_volume)
    assert Decimal(z.candidate_trade_gross_usd)==exact
    assert proxy==Decimal("100.03")
    assert exact==Decimal("100.025")
    assert exact!=proxy
    assert z.consolidated_population_proven is False
