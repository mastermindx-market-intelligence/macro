"""Fixed, source-free C15 timing-utility falsifiers, never market-data proof."""
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engine.market_microstructure.paired_entry_utility import (
    SCHEMA, evaluate_same_candidate,
)

D = 1_000_000_000
MIN = 60 * D
T = int(datetime(2026, 10, 8, 10, 0, tzinfo=ZoneInfo("America/New_York")).timestamp()) * D
SHA = lambda letter: letter * 64


def setup(*, direction=1):
    # Representative qualified receipts are FAKE SYNTHETIC SHA strings.
    c = {
        "candidate_id":"frozen-radar-candidate-8","ticker":"AMD",
        "session":"2026-10-08:RTH","source_mode":"ACTUAL_AS_SEEN",
        "source_receipt_sha256":SHA("a"),"candidate_source_available_ns":T-D,
        "decision_ns":T,"deadline_ns":T+2*MIN,"horizon_end_ns":T+30*MIN,
        "horizon_trading_minutes":30,"calendar_receipt_sha256":SHA("b"),
        "direction":direction,"research_quantity":"10",
        "initial_midpoint_usd":"100","max_quote_age_ns":5*D,
    }
    def policy(role,entry_bid,entry_ask,exit_bid="102",exit_ask="102.1"):
        start=T+D if role=="baseline" else T+MIN
        return {
            "candidate_id":c["candidate_id"],"role":role,
            "state":"SIMULATED_FULL","policy_receipt_sha256":SHA("c" if role=="baseline" else "d"),
            "policy_frozen_ns":T-MIN,
            "consumer_available_ns":None if role=="baseline" else T-D,
            "consumer_receipt_sha256":None if role=="baseline" else SHA("7"),
            "entry_decision_ns":start,
            "entry_quote_event_ns":start-D//2,
            "entry_quote_available_ns":start-D//3,
            "entry_quote_receipt_sha256":SHA("e"),
            "entry_bid_usd":entry_bid, "entry_ask_usd":entry_ask,
            "entry_bid_size_shares":"15","entry_ask_size_shares":"15",
            "exit_quote_event_ns":T+30*MIN-D,
            "exit_quote_available_ns":T+30*MIN+D//3,
            "exit_quote_receipt_sha256":SHA("f"),
            "exit_bid_usd":exit_bid,"exit_ask_usd":exit_ask,
            "exit_bid_size_shares":"15","exit_ask_size_shares":"15",
            "fees_usd":"1",
            "abstain_receipt_sha256":None,"abstain_available_ns":None,
            "unobservable_reason":None,
        }
    b=policy("baseline","100.9","101")
    h=policy("challenger","99.9","100")
    args={
        "candidate":c,"baseline":b,"challenger":h,
        "evaluation_cutoff_ns":T+30*MIN+2*D,
        "source_watermark_ns":T+30*MIN,
        "watermark_received_ns":T+30*MIN+D,
        "market_health":"NORMAL","market_health_receipt_sha256":SHA("1"),
    }
    return args


def run(a):
    return evaluate_same_candidate(**a)


def bps(result,which):
    row=result[which+"_bps"]
    return (int(row["numerator"]),int(row["denominator"]))


def test_same_candidate_exact_paired_quote_simulation():
    r=run(setup())
    assert r["schema"]==SCHEMA
    assert r["state"]=="PAIRED_RESEARCH_UTILITY"
    assert bps(r,"baseline")==(90,1)
    assert bps(r,"challenger")==(190,1)
    assert bps(r,"delta")==(100,1)
    assert r["delta_bps"]["display_bps_12dp"]=="100.000000000000"
    assert r["source_authenticated"] is False
    assert r["prospective_promotion"] is False
    assert r["predictive_rank_trading_alert_authority"] is False
    assert r["simulated_execution_not_fill"] is True
    assert r["actual_consumer_delivery_proven"] is False
    assert r["calendar_qualified_by_this_function"] is False
    assert r["supplied_input_first_knowable_ns"] == T+30*MIN+D
    assert r["supplied_input_first_knowable_not_consumer_receipt"] is True


def test_same_direction_and_research_quantity_never_reselected():
    a=setup(direction=-1)
    a["baseline"].update(entry_bid_usd="99",entry_ask_usd="99.1",
                         exit_bid_usd="97.9",exit_ask_usd="98")
    a["challenger"].update(entry_bid_usd="98",entry_ask_usd="98.1",
                           exit_bid_usd="97.9",exit_ask_usd="98")
    r=run(a)
    assert bps(r,"baseline")==(90,1)
    assert bps(r,"challenger")==(-10,1)
    assert bps(r,"delta")==(-100,1)


def test_policy_abstention_is_real_policy_zero_not_positive_gain():
    a=setup()
    h=a["challenger"]
    for k in ("entry_quote_event_ns","entry_quote_available_ns","entry_quote_receipt_sha256",
              "entry_bid_usd","entry_ask_usd","entry_bid_size_shares","entry_ask_size_shares",
              "exit_quote_event_ns","exit_quote_available_ns","exit_quote_receipt_sha256",
              "exit_bid_usd","exit_ask_usd","exit_bid_size_shares","exit_ask_size_shares","fees_usd"):
        h[k]=None
    h["state"]="FROZEN_ABSTAIN"
    h["abstain_receipt_sha256"]=SHA("0")
    h["abstain_available_ns"]=T+MIN+D
    r=run(a)
    assert bps(r,"baseline")==(90,1)
    assert bps(r,"challenger")==(0,1)
    assert bps(r,"delta")==(-90,1)


def test_missing_market_source_is_not_abstention_zero():
    a=setup()
    h=a["challenger"]
    for k in ("entry_decision_ns","entry_quote_event_ns","entry_quote_available_ns",
              "entry_quote_receipt_sha256","entry_bid_usd","entry_ask_usd",
              "entry_bid_size_shares","entry_ask_size_shares","exit_quote_event_ns",
              "exit_quote_available_ns","exit_quote_receipt_sha256",
              "exit_bid_usd","exit_ask_usd","exit_bid_size_shares","exit_ask_size_shares","fees_usd"):
        h[k]=None
    h["state"]="UNOBSERVABLE"
    h["unobservable_reason"]="SOURCE_GAP"
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["challenger_bps"] is None and r["delta_bps"] is None
    assert r["reason"]["challenger"]=="SOURCE_GAP"


@pytest.mark.parametrize("target", ["source_watermark_ns", "watermark_received_ns",
                                      "evaluation_cutoff_ns"])
def test_forward_maturity_never_backdates(target):
    a=setup()
    a[target]=T+30*MIN-D if target!="watermark_received_ns" else T+30*MIN+3*D
    r=run(a)
    assert r["state"]=="NOT_MATURE"
    assert r["delta_bps"] is None


@pytest.mark.parametrize("health",["HALTED","UNKNOWN"])
def test_halt_unknown_source_is_censored_not_flat_utility(health):
    a=setup()
    a["market_health"]=health
    r=run(a)
    assert r["state"]=="CENSORED"
    assert r["delta_bps"] is None


@pytest.mark.parametrize("misfit", [
    ("candidate_id","other"),
    ("role","baseline"),
    ("policy_frozen_ns",T+D),
])
def test_policy_identity_and_freeze_boundaries(misfit):
    a=setup()
    a["challenger"][misfit[0]]=misfit[1]
    with pytest.raises(ValueError):
        run(a)


def test_late_overlay_is_not_retroactively_relabelled_as_seen():
    a=setup()
    a["challenger"]["consumer_available_ns"]=T+1
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["challenger"]=="OVERLAY_ARRIVED_AFTER_ORIGINAL_DECISION"
    assert r["delta_bps"] is None


def test_baseline_cannot_claim_the_challenger_feature():
    a=setup()
    a["baseline"]["consumer_available_ns"]=T-D
    with pytest.raises(ValueError,match="baseline"):
        run(a)


@pytest.mark.parametrize("field,value", [
    ("entry_quote_event_ns",T+D),
    ("entry_quote_available_ns",T+2*D),
    ("entry_quote_event_ns",T-6*D),
])
def test_entry_uses_previous_knowable_fresh_quote_only(field,value):
    a=setup()
    a["baseline"][field]=value
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["delta_bps"] is None


@pytest.mark.parametrize("field,value", [
    ("exit_quote_event_ns",T+30*MIN),
    ("exit_quote_available_ns",T+30*MIN+3*D),
    ("exit_quote_event_ns",T+30*MIN-6*D),
])
def test_exit_only_after_maturity_and_fresh_prior_quote(field,value):
    a=setup()
    a["challenger"][field]=value
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["delta_bps"] is None


def test_earliest_policy_entry_is_limited_by_original_candidate_cutoff():
    a=setup()
    a["baseline"]["entry_decision_ns"]=T-D
    with pytest.raises(ValueError,match="entry out"):
        run(a)


def test_policy_abstention_cannot_hide_missing_source_or_quote():
    a=setup()
    a["challenger"]["state"]="FROZEN_ABSTAIN"
    a["challenger"]["abstain_receipt_sha256"]=SHA("9")
    a["challenger"]["abstain_available_ns"]=T+MIN+D
    with pytest.raises(ValueError,match="source unknown cannot"):
        run(a)


@pytest.mark.parametrize("wrong", ["2026-10-09:RTH","2026-10-10:RTH"])
def test_cross_session_claim_fails(wrong):
    a=setup()
    a["candidate"]["session"]=wrong
    with pytest.raises(ValueError,match="outside nominal"):
        run(a)


def test_weekend_and_after_hours_fail_nominal_calendar():
    a=setup()
    saturday=datetime(2026,10,10,10,0,tzinfo=ZoneInfo("America/New_York"))
    a["candidate"]["decision_ns"]=int(saturday.timestamp())*D
    a["candidate"]["deadline_ns"]=a["candidate"]["decision_ns"]+2*MIN
    a["candidate"]["horizon_end_ns"]=a["candidate"]["decision_ns"]+30*MIN
    a["candidate"]["session"]="2026-10-10:RTH"
    with pytest.raises(ValueError,match="outside nominal"):
        run(a)
    a=setup()
    evening=int(datetime(2026,10,8,17,0,tzinfo=ZoneInfo("America/New_York")).timestamp())*D
    a["candidate"]["decision_ns"]=evening
    a["candidate"]["deadline_ns"]=evening+2*MIN
    a["candidate"]["horizon_end_ns"]=evening+30*MIN
    with pytest.raises(ValueError,match="outside nominal"):
        run(a)


def test_horizon_is_external_attestation_not_automatically_qualified():
    a=setup()
    a["candidate"]["horizon_trading_minutes"]=29
    with pytest.raises(ValueError,match="trading-minute horizon"):
        run(a)
    a=setup()
    assert run(a)["calendar_qualified_by_this_function"] is False


@pytest.mark.parametrize("field,value", [
    ("research_quantity","0"),("initial_midpoint_usd","0"),
    ("research_quantity","1e99"),("initial_midpoint_usd","nan"),
])
def test_amounts_finite_positive_fixed_without_exponent_inflation(field,value):
    a=setup()
    a["candidate"][field]=value
    with pytest.raises(ValueError):
        run(a)


def test_return_display_does_not_hide_nonzero_exact_result():
    a=setup()
    a["candidate"]["initial_midpoint_usd"]="100"
    a["challenger"]["entry_ask_usd"]="100.000000000000000000000000000001"
    a["baseline"]["entry_ask_usd"]="100.000000000000000000000000000002"
    a["challenger"]["entry_bid_usd"]="100"
    a["baseline"]["entry_bid_usd"]="100"
    a["baseline"]["fees_usd"]="0"
    a["challenger"]["fees_usd"]="0"
    r=run(a)
    assert r["state"]=="PAIRED_RESEARCH_UTILITY"
    assert int(r["delta_bps"]["numerator"]) != 0
    assert r["delta_bps"]["display_only_rounded"] is True
    assert r["delta_bps"]["display_bps_12dp"]=="0.000000000000"


def test_final_vintage_remains_research_not_pit_proof():
    a=setup()
    a["candidate"]["source_mode"]="FINAL_VINTAGE"
    r=run(a)
    assert r["source_mode"]=="FINAL_VINTAGE"
    assert r["prospective_promotion"] is False
    assert r["source_authenticated"] is False



def test_missing_overlay_receipt_is_not_an_earlier_available_feature():
    a=setup()
    a["challenger"]["consumer_receipt_sha256"]=None
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["challenger"]=="OVERLAY_CONSUMER_AVAILABILITY_NOT_PROVEN"


def test_candidate_original_snapshot_must_exist_by_original_decision():
    a=setup()
    a["candidate"]["candidate_source_available_ns"]=T+1
    with pytest.raises(ValueError,match="original source arrived"):
        run(a)


@pytest.mark.parametrize("role,field",[
    ("baseline","entry_quote_available_ns"),
    ("challenger","exit_quote_available_ns"),
])
def test_quote_receipt_cannot_precede_sip_event(role,field):
    a=setup()
    row=a[role]
    eventkey=("entry_quote_event_ns" if field.startswith("entry")
              else "exit_quote_event_ns")
    row[field]=row[eventkey]-1
    r=run(a)
    assert r["state"]=="UNOBSERVABLE" and r["delta_bps"] is None


def test_crossing_side_prices_are_derived_not_picked_by_challenger():
    a=setup()
    # A better BID may not improve a BUY entry; buyer crosses at ASK.
    a["challenger"]["entry_bid_usd"]="99.99"
    assert bps(run(a),"delta")==(100,1)
    # A more expensive ASK worsens the buyer's entry.
    a["challenger"]["entry_ask_usd"]="101.5"
    assert bps(run(a),"delta")==(-50,1)


@pytest.mark.parametrize("field",["entry_ask_size_shares","exit_bid_size_shares"])
def test_top_of_book_cannot_simulate_more_shares_than_displayed(field):
    a=setup()
    a["challenger"][field]="9.999"
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["challenger"]=="INSUFFICIENT_DISPLAYED_TOP_SIZE"


def test_bid_ask_crossed_or_locked_is_not_an_eligible_quote():
    a=setup()
    a["baseline"]["entry_bid_usd"]="101"
    with pytest.raises(ValueError,match="locked or crossed"):
        run(a)


def test_claiming_30_trading_minutes_does_not_override_real_timestamp_distance():
    a=setup()
    a["candidate"]["horizon_end_ns"]-=MIN
    with pytest.raises(ValueError,match="horizon mismatch"):
        run(a)


def test_abstention_available_after_frozen_deadline_is_rejected():
    a=setup()
    h=a["challenger"]
    for field in (
        "entry_quote_event_ns","entry_quote_available_ns","entry_quote_receipt_sha256",
        "exit_quote_event_ns","exit_quote_available_ns","exit_quote_receipt_sha256",
        "entry_bid_usd","entry_ask_usd","entry_bid_size_shares","entry_ask_size_shares",
        "exit_bid_usd","exit_ask_usd","exit_bid_size_shares","exit_ask_size_shares",
        "fees_usd"
    ):
        h[field]=None
    h["state"]="FROZEN_ABSTAIN"
    h["abstain_receipt_sha256"]=SHA("9")
    h["abstain_available_ns"]=T+3*MIN
    with pytest.raises(ValueError,match="abstention not knowable"):
        run(a)


def test_source_watermark_receipt_before_original_market_time_is_rejected():
    a=setup()
    a["watermark_received_ns"]=a["source_watermark_ns"]-1
    with pytest.raises(ValueError,match="watermark receipt"):
        run(a)



def test_invalid_original_clock_is_typed_refusal_not_unhandled_compare():
    a=setup()
    a["candidate"]["decision_ns"]=None
    with pytest.raises(ValueError,match="native clock invalid"):
        run(a)


def test_typed_no_source_is_not_replaced_with_zero_for_future_window():
    a=setup()
    a["source_watermark_ns"]=a["candidate"]["horizon_end_ns"]-1
    r=run(a)
    assert r["state"]=="NOT_MATURE" and r["delta_bps"] is None


def test_single_nanosecond_entry_quote_arrival_after_decision_fails():
    a=setup()
    a["challenger"]["entry_quote_available_ns"]=a["challenger"]["entry_decision_ns"]+1
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["challenger"]=="ENTRY_QUOTE_NOT_KNOWABLE_OR_STALE"



def test_component_arrival_lower_bound_changes_with_later_valid_exit_receipt():
    a=setup()
    a["challenger"]["exit_quote_available_ns"]=T+30*MIN+3*D//2
    result=run(a)
    assert result["state"]=="PAIRED_RESEARCH_UTILITY"
    assert result["supplied_input_first_knowable_ns"]==T+30*MIN+3*D//2
    assert result["actual_consumer_delivery_proven"] is False



def test_same_nanosecond_candidate_receipt_cannot_self_authorize():
    a=setup()
    a["candidate"]["candidate_source_available_ns"]=T
    with pytest.raises(ValueError,match="original source arrived"):
        run(a)


def test_same_nanosecond_overlay_is_unordered_without_native_sequence():
    a=setup()
    a["challenger"]["consumer_available_ns"]=T
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["challenger"]=="OVERLAY_ARRIVED_AFTER_ORIGINAL_DECISION"


def test_freezing_policy_at_same_decision_nanosecond_is_not_prior():
    a=setup()
    a["baseline"]["policy_frozen_ns"]=T
    with pytest.raises(ValueError,match="not frozen before"):
        run(a)


def test_quote_arriving_at_simulated_fill_nanosecond_is_unordered():
    a=setup()
    a["baseline"]["entry_quote_available_ns"]=a["baseline"]["entry_decision_ns"]
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["baseline"]=="ENTRY_QUOTE_NOT_KNOWABLE_OR_STALE"


def test_derived_outcome_not_admitted_at_equal_evaluation_receipt():
    a=setup()
    a["watermark_received_ns"]=a["evaluation_cutoff_ns"]
    r=run(a)
    assert r["state"]=="NOT_MATURE"


def test_quote_arriving_at_cutoff_nano_is_not_a_previous_eligible_receipt():
    a=setup()
    a["challenger"]["exit_quote_available_ns"]=a["evaluation_cutoff_ns"]
    r=run(a)
    assert r["state"]=="UNOBSERVABLE"
    assert r["reason"]["challenger"]=="EXIT_QUOTE_NOT_KNOWABLE_OR_STALE"
