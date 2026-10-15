"""Fixed, source-free C15 timing-utility falsifiers, never market-data proof."""
from datetime import datetime
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
        "anchor_quote_event_ns":T-D,
        "anchor_quote_available_ns":T-D//2,
        "anchor_quote_receipt_sha256":SHA("8"),
        "anchor_bid_usd":"99.9","anchor_ask_usd":"100.1",
        "anchor_bid_size_shares":"25","anchor_ask_size_shares":"25",
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
            "exit_quote_available_ns":T+30*MIN-D//3,
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



def test_component_arrival_lower_bound_is_not_fake_consumer_receipt():
    a=setup()
    # Every eligible exit quote must have arrived BEFORE H, while the
    # evaluation watermark arrives after H. It bounds first knowability.
    a["challenger"]["exit_quote_available_ns"]=T+30*MIN-D//2
    a["baseline"]["exit_quote_available_ns"]=T+30*MIN-D//2
    result=run(a)
    assert result["state"]=="PAIRED_RESEARCH_UTILITY"
    assert result["supplied_input_first_knowable_ns"]==T+30*MIN+D
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



# Adversarial source-grain falsifiers added after published source review.
# The existing v0 candidate returned apparent simulated fills from post-horizon
# quotes and admitted different terminal quote snapshots for the same candidate.
def test_exit_quote_received_after_horizon_is_not_a_horizon_fill():
    a=setup()
    a["baseline"]["exit_quote_available_ns"]=T+30*MIN+1
    result=run(a)
    assert result["state"]=="UNOBSERVABLE"
    assert result["reason"]["baseline"]=="EXIT_QUOTE_NOT_KNOWABLE_OR_STALE"


def test_two_policy_arms_cannot_choose_different_terminal_quotes():
    a=setup()
    a["challenger"]["exit_bid_usd"]="107"
    a["challenger"]["exit_ask_usd"]="107.1"
    with pytest.raises(ValueError,match="terminal quote"):
        run(a)


def test_initial_notional_anchor_cannot_be_arbitrarily_rescaled():
    a=setup()
    a["candidate"]["initial_midpoint_usd"]="1000000"
    with pytest.raises(ValueError,match="anchor midpoint"):
        run(a)


@pytest.mark.parametrize(("field", "value", "expected"), [
    ("anchor_quote_event_ns", T-6*D, "anchor quote not knowable"),
    ("anchor_quote_available_ns", T, "anchor quote not knowable"),
    ("anchor_quote_available_ns", T-2*D, "anchor quote not knowable"),
    ("anchor_quote_receipt_sha256", "A"*64, "digest missing"),
])
def test_original_notional_anchor_rejects_unknown_or_stale_source(field, value, expected):
    a=setup()
    a["candidate"][field]=value
    with pytest.raises(ValueError, match=expected):
        run(a)


@pytest.mark.parametrize(("bid", "ask"), [
    ("100.1", "100.1"), ("100.2", "100.1"),
    ("0", "100.1"), ("99.9", "1e30"),
])
def test_original_anchor_bid_ask_must_be_real_bounded_positive_pair(bid, ask):
    a=setup()
    a["candidate"]["anchor_bid_usd"]=bid
    a["candidate"]["anchor_ask_usd"]=ask
    with pytest.raises(ValueError):
        run(a)


@pytest.mark.parametrize(("field","value"), [
    ("exit_quote_event_ns", T+30*MIN-D//2),
    ("exit_quote_available_ns", T+30*MIN-D//2),
    ("exit_quote_receipt_sha256", SHA("9")),
    ("exit_bid_usd", "102.05"),
    ("exit_ask_usd", "102.2"),
    ("exit_bid_size_shares", "14"),
    ("exit_ask_size_shares", "14"),
])
def test_same_candidate_terminal_quote_is_one_source_vintage(field, value):
    a=setup()
    a["challenger"][field]=value
    with pytest.raises(ValueError, match="terminal quote"):
        run(a)


def test_quote_arriving_at_exact_horizon_cannot_simulate_exit_at_that_time():
    a=setup()
    a["baseline"]["exit_quote_available_ns"]=T+30*MIN
    result=run(a)
    assert result["state"]=="UNOBSERVABLE"
    assert result["reason"]["baseline"]=="EXIT_QUOTE_NOT_KNOWABLE_OR_STALE"


def test_valid_two_policy_shared_terminal_quote_is_reproducible():
    a=setup()
    b=a["baseline"]
    h=a["challenger"]
    fields=("exit_quote_event_ns","exit_quote_available_ns","exit_quote_receipt_sha256",
            "exit_bid_usd","exit_ask_usd","exit_bid_size_shares","exit_ask_size_shares")
    assert all(b[key]==h[key] for key in fields)
    result=run(a)
    assert bps(result,"delta")==(100,1)
    assert result["supplied_input_first_knowable_ns"]==a["watermark_received_ns"]
    assert result["actual_consumer_delivery_proven"] is False


from engine.market_microstructure.paired_entry_utility import (
    COHORT_SCHEMA, reconcile_frozen_candidate_cohort,
)


def registered_row(args):
    c=args["candidate"]
    return {
        "candidate_id":c["candidate_id"],"ticker":c["ticker"],
        "session":c["session"],"source_mode":c["source_mode"],
        "original_decision_ns":c["decision_ns"],
        "horizon_end_ns":c["horizon_end_ns"],
        "source_receipt_sha256":c["source_receipt_sha256"],
        "calendar_receipt_sha256":c["calendar_receipt_sha256"],
        "candidate_source_available_ns":c["candidate_source_available_ns"],
        "deadline_ns":c["deadline_ns"],
        "direction":c["direction"],
        "research_quantity":c["research_quantity"],
        "initial_midpoint_usd":c["initial_midpoint_usd"],
        "max_quote_age_ns":c["max_quote_age_ns"],
        "anchor_quote_event_ns":c["anchor_quote_event_ns"],
        "anchor_quote_available_ns":c["anchor_quote_available_ns"],
        "anchor_quote_receipt_sha256":c["anchor_quote_receipt_sha256"],
        "anchor_bid_usd":c["anchor_bid_usd"],
        "anchor_ask_usd":c["anchor_ask_usd"],
        "anchor_bid_size_shares":c["anchor_bid_size_shares"],
        "anchor_ask_size_shares":c["anchor_ask_size_shares"],
    }


def second_candidate():
    a=setup()
    a["candidate"]["candidate_id"]="frozen-radar-candidate-9"
    a["candidate"]["source_receipt_sha256"]=SHA("2")
    a["baseline"]["candidate_id"]=a["candidate"]["candidate_id"]
    a["challenger"]["candidate_id"]=a["candidate"]["candidate_id"]
    return a


def accounted(expected, reports):
    return reconcile_frozen_candidate_cohort(
        expected_candidates=expected,supplied_evaluations=reports,
        frozen_manifest_sha256=SHA("a"),
    )


def test_cohort_exact_full_denominator_and_ratio_are_software_only():
    a=setup()
    b=second_candidate()
    result=accounted([registered_row(a),registered_row(b)], [run(a),run(b)])
    assert result["schema"]==COHORT_SCHEMA
    assert result["state"]=="ALL_FROZEN_CANDIDATES_ACCOUNTED_SOFTWARE_ONLY"
    assert result["n_expected"]==2 and result["n_supplied"]==2
    assert result["n_missing"]==0 and result["n_complete_software_pairs"]==2
    assert int(result["observed_pair_subset_mean_bps"]["numerator"])==100
    assert int(result["observed_pair_subset_mean_bps"]["denominator"])==1
    assert result["primary_population_mean_bps"] is None
    for field in ("source_authenticated", "actual_consumer_delivery_proven",
                  "empirical_source_qualified", "inference_or_power_established",
                  "trial_ledger_written", "prospective_promotion",
                  "predictive_rank_trading_alert_authority"):
        assert result[field] is False


def test_cohort_missing_candidate_cannot_be_excluded_from_denominator():
    a=setup()
    b=second_candidate()
    result=accounted([registered_row(a),registered_row(b)], [run(a)])
    assert result["state"]=="MISSING_EXPECTED_CANDIDATE_REPORTS"
    assert result["n_expected"]==2 and result["n_supplied"]==1
    assert result["n_missing"]==1
    assert result["missing_candidate_ids_private_only"]==[b["candidate"]["candidate_id"]]
    assert result["primary_population_mean_bps"] is None


def test_cohort_zero_reports_is_not_zero_market_or_favorable_abstention():
    a=setup()
    result=accounted([registered_row(a)], [])
    assert result["n_missing"]==1
    assert result["n_complete_software_pairs"]==0
    assert result["observed_pair_subset_mean_bps"] is None
    assert result["primary_population_mean_bps"] is None


def test_cohort_keeps_censored_immature_and_unobservable_in_original_counts():
    a=setup()
    b=second_candidate()
    c=setup()
    c["candidate"]["candidate_id"]="frozen-radar-candidate-10"
    c["baseline"]["candidate_id"]="frozen-radar-candidate-10"
    c["challenger"]["candidate_id"]="frozen-radar-candidate-10"
    a["market_health"]="HALTED"
    b["source_watermark_ns"]=T+30*MIN-1
    c["challenger"]["consumer_receipt_sha256"]=None
    result=accounted(
        [registered_row(a),registered_row(b),registered_row(c)],
        [run(a),run(b),run(c)],
    )
    assert result["n_expected"]==3
    assert result["n_complete_software_pairs"]==0
    assert result["by_state"]["CENSORED"]==1
    assert result["by_state"]["NOT_MATURE"]==1
    assert result["by_state"]["UNOBSERVABLE"]==1
    assert result["observed_pair_subset_mean_bps"] is None


@pytest.mark.parametrize("attack",[
    "extra_candidate", "duplicate_report", "duplicate_expected",
    "wrong_source", "wrong_calendar", "wrong_ticker", "wrong_directional_state",
    "forged_delta", "forged_display", "extra_field", "fake_market_authority",
])
def test_cohort_rejects_candidate_or_result_tampering(attack):
    a=setup()
    expected=[registered_row(a)]
    result=run(a)
    rows=[result]
    if attack=="extra_candidate":
        rows[0]["candidate_id"]="unregistered-candidate"
    elif attack=="duplicate_report":
        rows.append(dict(result))
    elif attack=="duplicate_expected":
        expected.append(dict(expected[0]))
    elif attack=="wrong_source":
        rows[0]["candidate_source_receipt_sha256"]=SHA("c")
    elif attack=="wrong_calendar":
        rows[0]["calendar_receipt_sha256"]=SHA("c")
    elif attack=="wrong_ticker":
        rows[0]["ticker"]="SPY"
    elif attack=="wrong_directional_state":
        rows[0]["state"]="PAIRED_SHADOW"
    elif attack=="forged_delta":
        rows[0]["delta_bps"]["numerator"]="999"
    elif attack=="forged_display":
        rows[0]["delta_bps"]["display_bps_12dp"]="999.000000000000"
    elif attack=="extra_field":
        rows[0]["trading_signal"]="BUY"
    elif attack=="fake_market_authority":
        rows[0]["source_authenticated"]=True
    with pytest.raises(ValueError):
        accounted(expected, rows)


def test_cohort_never_pools_final_vintage_with_actual_as_seen():
    a=setup()
    b=second_candidate()
    b["candidate"]["source_mode"]="FINAL_VINTAGE"
    with pytest.raises(ValueError,match="must not be pooled"):
        accounted([registered_row(a),registered_row(b)],[run(a),run(b)])


def test_cohort_cannot_make_unmeasured_result_a_success():
    a=setup()
    a["market_health"]="HALTED"
    row=run(a)
    row["delta_bps"]={"numerator":"0","denominator":"1",
                      "display_bps_12dp":"0.000000000000",
                      "display_only_rounded":True}
    with pytest.raises(ValueError,match="dressed as measured"):
        accounted([registered_row(a)],[row])


def test_cohort_denominator_is_hard_bounded_not_an_unlimited_load():
    a=setup()
    expected=[registered_row(a)]*1001
    with pytest.raises(ValueError,match="invalid frozen denominator"):
        accounted(expected,[])



@pytest.mark.parametrize(("which", "value", "error"), [
    ("supplied_input_first_knowable_ns", T+30*MIN-1, "chronologically impossible"),
    ("supplied_input_first_knowable_ns", T+30*MIN+3*D, "chronologically impossible"),
    ("evaluation_cutoff_ns", T+30*MIN+D, "chronologically impossible"),
])
def test_cohort_paired_result_cannot_backdate_or_foredate_label(which,value,error):
    a=setup()
    result=run(a)
    result[which]=value
    with pytest.raises(ValueError,match=error):
        accounted([registered_row(a)],[result])


@pytest.mark.parametrize(("state", "reason"), [
    ("CENSORED", "HORIZON_OR_WATERMARK_NOT_KNOWABLE"),
    ("NOT_MATURE", "HALTED_OR_UNKNOWN_MARKET"),
    ("UNOBSERVABLE", {"baseline":None,"challenger":None}),
    ("UNOBSERVABLE", {"baseline":None,"challenger":"FAKE_WIN"}),
])
def test_cohort_rejects_false_nonpaired_reason(state,reason):
    a=setup()
    a["market_health"]="HALTED"
    result=run(a)
    result["state"]=state
    result["reason"]=reason
    with pytest.raises(ValueError,match="false|invalid typed"):
        accounted([registered_row(a)],[result])


def test_cohort_rejects_unhashable_source_mode_as_typed_refusal():
    a=setup()
    row=registered_row(a)
    row["source_mode"]=["ACTUAL_AS_SEEN"]
    with pytest.raises(ValueError,match="source mode inconsistent"):
        accounted([row],[run(a)])


def test_cohort_rejects_unhashable_state_as_typed_refusal():
    a=setup()
    result=run(a)
    result["state"]={"state":"PAIRED_RESEARCH_UTILITY"}
    with pytest.raises(ValueError,match="unrecognized evaluation outcome"):
        accounted([registered_row(a)],[result])


def test_cohort_paired_fraction_must_match_both_policy_utilities():
    a=setup()
    result=run(a)
    result["baseline_bps"]["numerator"]="100"
    result["baseline_bps"]["display_bps_12dp"]="100.000000000000"
    with pytest.raises(ValueError,match="delta not conserved"):
        accounted([registered_row(a)],[result])


# Original published v0.2 incorrectly leaked TypeError/InvalidOperation for
# legal JSON-shaped but malformed untrusted evidence. All contract refusals
# must be typed ValueError, never an implicit host-language exception.
from fractions import Fraction
from engine.market_microstructure.paired_entry_utility import (
    _exact_bp, _frozen_paired_rational,
)


def test_unhashable_candidate_source_mode_is_typed_refusal():
    a = setup()
    a["candidate"]["source_mode"] = ["ACTUAL_AS_SEEN"]
    with pytest.raises(ValueError, match="invalid source mode"):
        run(a)


def test_unhashable_policy_state_is_typed_refusal():
    a = setup()
    a["baseline"]["state"] = {"state": "SIMULATED_FULL"}
    with pytest.raises(ValueError, match="invalid state"):
        run(a)


def test_unhashable_source_missing_reason_is_typed_refusal():
    a = setup()
    a["baseline"]["state"] = "UNOBSERVABLE"
    a["baseline"]["unobservable_reason"] = ["SOURCE_GAP"]
    with pytest.raises(ValueError, match="missing typed source failure"):
        run(a)


def test_extreme_canonical_but_untrusted_ratio_uses_typed_refusal():
    ratio = {
        "numerator": "9" * 1024,
        "denominator": "1",
        "display_bps_12dp": "0.000000000000",
        "display_only_rounded": True,
    }
    with pytest.raises(ValueError, match="ratio/display incompatible"):
        _frozen_paired_rational(ratio, "cohort.adversarial_ratio")


@pytest.mark.parametrize(("value", "expected"), [
    (Fraction(1, 2_000_000_000_000), "0.000000000000"),
    (Fraction(3, 2_000_000_000_000), "0.000000000002"),
    (Fraction(-1, 2_000_000_000_000), "-0.000000000000"),
    (Fraction(-3, 2_000_000_000_000), "-0.000000000002"),
    (Fraction(1, 3), "0.333333333333"),
])
def test_exact_display_uses_half_even_without_changing_source_fraction(value, expected):
    output = _exact_bp(value)
    assert output["numerator"] == str(value.numerator)
    assert output["denominator"] == str(value.denominator)
    assert output["display_bps_12dp"] == expected
    assert output["display_only_rounded"] is True


# Scientific acceptance red test: the *original registered candidate's*
# direction, quantity and midpoint basis cannot change after the freeze.
# Prior cohort v0 did not carry these identities and silently accepted every
# altered label under the same candidate/source receipt.
@pytest.mark.parametrize("mutation",[
    {"direction":-1},
    {"research_quantity":"5"},
    {"deadline_ns":T+3*MIN},
    {"candidate_source_available_ns":T-2*D},
    {"anchor_quote_receipt_sha256":SHA("6")},
    {"anchor_quote_event_ns":T-2*D},
    {"anchor_bid_size_shares":"30"},
    {"max_quote_age_ns":4*D},
    {"initial_midpoint_usd":"200", "anchor_bid_usd":"199.9", "anchor_ask_usd":"200.1"},
])
def test_frozen_cohort_rejects_post_decision_candidate_economic_basis_change(mutation):
    original = setup()
    changed = setup()
    changed["candidate"].update(mutation)
    assert run(changed)["state"] == "PAIRED_RESEARCH_UTILITY"
    with pytest.raises(ValueError, match="frozen candidate"):
        accounted([registered_row(original)], [run(changed)])


@pytest.mark.parametrize(("key","value"),[
    ("direction",-1),
    ("research_quantity","2"),
    ("deadline_ns",T+4*MIN),
    ("initial_midpoint_usd","99"),
    ("anchor_quote_receipt_sha256",SHA("5")),
    ("anchor_bid_size_shares","1"),
])
def test_later_paired_label_cannot_forge_frozen_candidate_economic_identity(key,value):
    a=setup()
    label=run(a)
    label[key]=value
    with pytest.raises(ValueError,match="frozen candidate"):
        accounted([registered_row(a)],[label])


@pytest.mark.parametrize(("key","value"),[
    ("direction",0),
    ("candidate_source_available_ns",T),
    ("deadline_ns",T+31*MIN),
    ("max_quote_age_ns",6*D),
    ("initial_midpoint_usd","0"),
    ("anchor_quote_available_ns",T),
])
def test_denominator_manifest_rejects_invalid_unevaluated_candidate(key,value):
    a=setup()
    frozen=registered_row(a)
    frozen[key]=value
    with pytest.raises(ValueError):
        accounted([frozen],[])


def test_original_economic_basis_survives_censored_and_immature_results():
    for mode in ("HALTED", "NOT_MATURE"):
        a=setup()
        if mode=="HALTED": a["market_health"]="HALTED"
        else: a["source_watermark_ns"]=T+30*MIN-1
        r=run(a)
        frozen=registered_row(a)
        for key in ("direction","research_quantity","initial_midpoint_usd",
                    "anchor_quote_receipt_sha256","deadline_ns",
                    "candidate_source_available_ns"):
            assert r[key]==frozen[key]
        reconciled=accounted([frozen],[r])
        assert reconciled["state"]=="ALL_FROZEN_CANDIDATES_ACCOUNTED_SOFTWARE_ONLY"
        assert reconciled["primary_population_mean_bps"] is None
        assert reconciled["source_authenticated"] is False
