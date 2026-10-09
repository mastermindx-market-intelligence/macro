"""Point-in-time provisional trade/quote integration tests."""

import copy
import json
import unittest

from engine.tick_plane.stream_events import normalize_ws_event, FrameContractError
from engine.tick_plane.asof_nbbo import InFlightNBBO
from engine.tick_plane.print_observations import observe_provisional_trade
from engine.tick_plane.condition_policy import parse_condition_reference, evaluate_trade_conditions
from engine.tick_plane.exchange_reference import parse_exchange_reference, classify_trade_venue
from engine.tick_plane.quote_condition_policy import parse_quote_policy, POLICY_SCHEMA as QPOLICY_SCHEMA

BASE=1_791_417_600_000
RECV=BASE*1_000_000+100_000_000
SESSION="2026-10-08:RTH"


def wrap(row):
    return normalize_ws_event(
        json.dumps([row]).encode(), event_index=0,
        frame_received_ns=RECV,source_receipt_id="owner-captured-frame",
        session=SESSION,allowed_symbols={"SPY"})


def q(**more):
    x={"ev":"Q","sym":"SPY","t":BASE,"q":1,"bx":1,"bp":100.1,
       "bs":100,"ax":2,"ap":100.2,"as":200,"c":0,"i":[604]}
    x.update(more)
    return wrap(x)


def t(**more):
    x={"ev":"T","sym":"SPY","t":BASE+10,"q":2,"x":11,
       "i":"T0001","p":100.2,"s":100,"c":[0]}
    x.update(more)
    return wrap(x)


def condition_verdict(trade, *, decision=RECV+20_000_000):
    native={"asset_class":"stocks","data_types":["trade"],"type":"condition","id":0,
            "name":"Eligible fixture only","update_rules":{"consolidated":{
              "updates_volume":True,"updates_high_low":True,"updates_open_close":True}}}
    snapshot=parse_condition_reference(raw_response_bytes=json.dumps({
        "status":"OK","request_id":"fixture-reference","results":[native]}).encode(),
        reference_received_ns=RECV-1_000_000,
        source_receipt_id="fixture:original-reference")
    return evaluate_trade_conditions(trade_conditions=trade["trade_conditions"],
        reference=snapshot,decision_ns=decision,original_reference_custody_attested=True)


def venue_verdict(trade, *, decision=RECV+20_000_000):
    records=[{"asset_class":"stocks","id":11,"type":"exchange"},
             {"asset_class":"stocks","id":4,"type":"TRF"}]
    ref=parse_exchange_reference(raw_response_bytes=json.dumps({
        "status":"OK","request_id":"fixture-exchange-reference","results":records}).encode(),
        available_ns=RECV-1_000_000,
        source_receipt_id="fixture:original-exchange-reference")
    return classify_trade_venue(trade=trade,reference=ref,decision_ns=decision,
                                original_reference_custody_attested=True)


def quote_policy():
    data={"schema":QPOLICY_SCHEMA,"source_reference_sha256":"c"*64,
          "reviewer_receipt":"synthetic:reviewer:source-vintage",
          "unknown_action":"ABSTAIN",
          "allowed_quote_conditions":[0,1],
          "allowed_nbbo_indicators":[602,604,605]}
    return parse_quote_policy(
        original_policy_bytes=json.dumps(data).encode(),
        policy_received_ns=RECV-1000000,
        policy_receipt_id="synthetic:source-quote-policy")


def input_args(trade=None,**updates):
    trade = t() if trade is None else trade
    kw=dict(decision_ns=RECV+20_000_000,
            source_complete_through_ns=(BASE+10)*1_000_000,
            watermark_available_ns=RECV+10,
            watermark_receipt_id="source-owner-contiguous-tq-proof",
            source_completeness_attested=True,
            max_quote_age_ns=50_000_000,
            trade_condition_verdict=condition_verdict(trade),
            venue_reference_verdict=venue_verdict(trade),
            quote_condition_policy=quote_policy(),
            original_quote_policy_custody_attested=True)
    kw.update(updates)
    return kw


class ProvisionalObservationTests(unittest.TestCase):
    def setUp(self):
        self.ring=InFlightNBBO(session=SESSION,symbols={"SPY"})
        self.ring.ingest_quote(q())

    def observed(self, trade=None, **kw):
        trade=t() if trade is None else trade
        return observe_provisional_trade(trade,self.ring,
                                          **input_args(trade=trade,**kw))

    def test_buy_at_offer_is_proxy_not_institutional_proof(self):
        r=self.observed()
        self.assertEqual(r["state"],"MEASURED_SOURCE_PROXY")
        self.assertEqual(r["side_proxy"],"buy")
        self.assertEqual(r["gross_observed_notional_usd"],"10020.0")
        self.assertEqual(r["signed_notional_usd"],"10020.0")
        self.assertEqual(r["quote_age_ns"],10_000_000)
        self.assertEqual(r["correction_status"],"STREAM_PROVISIONAL_UNRECONCILED")
        self.assertEqual(r["authority"],"OBSERVATIONAL_PROVISIONAL_ONLY")
        self.assertIsNone(r["absorption_signal"])
        self.assertIsNone(r["forward_response_label"])

    def test_sell_at_bid_is_negative_proxy(self):
        r=self.observed(trade=t(p=100.1))
        self.assertEqual(r["side_proxy"],"sell")
        self.assertEqual(r["signed_notional_usd"],"-10010.0")

    def test_midpoint_stays_unsigned(self):
        r=self.observed(trade=t(p=100.15))
        self.assertEqual(r["side_proxy"],"mid")
        self.assertIsNone(r["signed_notional_usd"])

    def test_unqualified_trade_condition_cannot_be_silently_true(self):
        r=self.observed(trade_condition_verdict=None)
        self.assertEqual(r["reason"],"TRADE_CONDITION_POLICY_UNQUALIFIED")
        self.assertEqual(r["side_proxy"],"unclassified")

    def test_known_ineligible_condition_does_not_sign_print(self):
        bad=condition_verdict(t())
        bad["eligible_for_pressure"]=False
        r=self.observed(trade_condition_verdict=bad)
        self.assertEqual(r["state"],"INELIGIBLE")
        self.assertIsNone(r["signed_notional_usd"])

    def test_off_exchange_never_uses_reporting_sip_as_execution_quote(self):
        r=self.observed(trade=t(x=4,trfi=201))
        self.assertEqual(r["reason"],"TRF_OR_VENUE_CLOCK_UNQUALIFIED")
        self.assertIsNone(r["signed_notional_usd"])

    def test_uncertified_quote_conditions_yield_unknown(self):
        r=self.observed(quote_condition_policy=None)
        self.assertEqual(r["reason"],"QUOTE_CONDITION_POLICY_UNQUALIFIED")

    def test_unattested_source_capture_yields_unknown(self):
        r=self.observed(source_completeness_attested=False)
        self.assertEqual(r["reason"],"SOURCE_COMPLETENESS_UNATTESTED")

    def test_gap_fence_survives_a_fresh_sample(self):
        self.ring.mark_gap("SPY")
        r=self.observed()
        self.assertEqual(r["reason"],"SOURCE_GAP_QUARANTINED")

    def test_same_millisecond_trade_quote_is_unordered(self):
        self.ring.ingest_quote(q(t=BASE+10,q=2))
        r=self.observed()
        self.assertEqual(r["reason"],"UNORDERED_SAME_MILLISECOND")

    def test_valid_bid_ask_can_be_temporary_no_firm_quote(self):
        ring=InFlightNBBO(session=SESSION,symbols={"SPY"})
        ring.ingest_quote(q(**{"as":0}))
        tr=t()
        r=observe_provisional_trade(tr,ring,**input_args(trade=tr))
        self.assertEqual(r["reason"],"INVALID_OR_ONE_SIDED_NBBO")

    def test_trade_late_arrival_rejected(self):
        trade=t()
        trade["original_frame_received_ns"]=RECV+100_000_000
        r=self.observed(trade=trade)
        self.assertEqual(r["reason"],"TRADE_NOT_AVAILABLE_AT_DECISION")

    def test_fractional_shares_multiply_actual_decimal_size(self):
        tr=t(s=0,ds="0.375")
        r=self.observed(trade=tr)
        self.assertEqual(r["gross_observed_notional_usd"],"37.5750")
        self.assertEqual(r["side_proxy"],"buy")

    def test_observation_contains_source_receipt_but_not_raw_payload(self):
        r=self.observed()
        self.assertIsInstance(r["quote_source_receipt_id"],str)
        self.assertEqual(r["matched_quote_id"],f"{SESSION}:SPY:Q:1:{BASE*1_000_000}")
        self.assertNotIn("raw_frame_bytes",r)

    def test_quote_watermark_maturity_required(self):
        r=self.observed(source_complete_through_ns=(BASE+1)*1_000_000)
        self.assertEqual(r["reason"],"TRADE_WINDOW_NOT_COMPLETE")
 
    def test_trade_condition_receipt_and_native_codes_must_match_source_trade(self):
        ver=condition_verdict(t())
        ver["native_trade_conditions"]=[12]
        r=self.observed(trade_condition_verdict=ver)
        self.assertEqual(r["reason"],"TRADE_CONDITION_POLICY_UNQUALIFIED")

    def test_trade_condition_later_reference_clock_not_backdated(self):
        ver=condition_verdict(t())
        ver["reference_received_ns"]=RECV+25_000_000
        r=self.observed(trade_condition_verdict=ver)
        self.assertEqual(r["reason"],"TRADE_CONDITION_POLICY_UNQUALIFIED")

    def test_trade_condition_decision_time_mismatch_abstains(self):
        ver=condition_verdict(t())
        ver["decision_ns"]=RECV+100_000_000
        r=self.observed(trade_condition_verdict=ver)
        self.assertEqual(r["reason"],"TRADE_CONDITION_POLICY_UNQUALIFIED")

    def test_unknown_native_condition_does_not_default_to_buy_side(self):
        trade=t(c=[999])
        r=self.observed(trade=trade)
        self.assertEqual(r["reason"],"TRADE_CONDITION_POLICY_UNQUALIFIED")
        self.assertIsNone(r["signed_notional_usd"])

    def test_source_condition_vintage_receipt_is_exposed_by_reference(self):
        r=self.observed()
        self.assertEqual(len(r["trade_conditions_rules_ref"]),64)
        self.assertEqual(r["trade_condition_policy_reason"],
                         "CONSERVATIVE_PRICE_FORMING_CANDIDATE")


    def test_no_versioned_venue_verdict_never_signs(self):
        r=self.observed(venue_reference_verdict=None)
        self.assertEqual(r["reason"],"VENUE_REFERENCE_UNQUALIFIED")
        self.assertIsNone(r["signed_notional_usd"])

    def test_tampered_venue_identity_abstains(self):
        bad=venue_verdict(t())
        bad["native_exchange_id"]=62
        r=self.observed(venue_reference_verdict=bad)
        self.assertEqual(r["reason"],"VENUE_REFERENCE_UNQUALIFIED")

    def test_future_exchange_reference_cannot_backfill(self):
        bad=venue_verdict(t())
        bad["exchange_reference_received_ns"]=RECV+50_000_000
        r=self.observed(venue_reference_verdict=bad)
        self.assertEqual(r["reason"],"VENUE_REFERENCE_UNQUALIFIED")

    def test_positive_source_venue_receipt_survives_observation(self):
        r=self.observed()
        self.assertEqual(len(r["venue_reference_sha256"]),64)
        self.assertEqual(r["venue_admission_reason"],
                         "SOURCE_REFERENCE_EXCHANGE_CANDIDATE")

    def test_native_quote_condition_nonfirm_abstains_after_nbbo_lookup(self):
        ring=InFlightNBBO(session=SESSION,symbols={"SPY"})
        ring.ingest_quote(q(c=20))
        tr=t()
        result=observe_provisional_trade(tr,ring,**input_args(trade=tr))
        self.assertEqual(result["reason"],"QUOTE_CONDITION_NOT_FIRM_OR_UNKNOWN")
        self.assertIsNone(result["signed_notional_usd"])

    def test_native_quote_indicator_unrecognized_abstains(self):
        ring=InFlightNBBO(session=SESSION,symbols={"SPY"})
        ring.ingest_quote(q(i=[999]))
        tr=t()
        result=observe_provisional_trade(tr,ring,**input_args(trade=tr))
        self.assertEqual(result["reason"],"NON_ADMITTED_NBBO_INDICATOR")

    def test_quote_policy_later_than_original_decision_abstains(self):
        later=quote_policy()
        later["policy_received_ns"]=RECV+40_000_000
        result=self.observed(quote_condition_policy=later)
        self.assertEqual(result["reason"],"QUOTE_OR_POLICY_NOT_AVAILABLE_AT_DECISION")

    def test_quote_policy_custody_not_assumed_from_supplied_json(self):
        result=self.observed(original_quote_policy_custody_attested=False)
        self.assertEqual(result["reason"],"QUOTE_CONDITION_POLICY_UNQUALIFIED")

    def test_quote_policy_digest_survives_measured_record(self):
        result=self.observed()
        self.assertEqual(result["quote_conditions_rules_ref"],
                         quote_policy()["policy_sha256"])


from engine.tick_plane.captured_minute import (
    compose_captured_minute, CapturedMinuteRefusal,
)
from engine.tick_plane.quote_condition_policy import (
    parse_quote_policy, POLICY_SCHEMA as QPOLICY_SCHEMA,
)
from engine.tick_plane.minute_projection import MINUTE_NS


def captured_synthetic_window(*, special_condition=None):
    start=(BASE*1_000_000//MINUTE_NS)*MINUTE_NS
    start_ms=start//1_000_000
    end=start+MINUTE_NS
    decision=end+2_000_000_000
    trades=[
        {"ev":"T","sym":"SPY","t":start_ms+20000,"q":101,
         "x":11,"i":"synthetic-buyer","p":100.9,"s":10,"c":[0]},
        {"ev":"T","sym":"SPY","t":start_ms+40000,"q":102,
         "x":11,"i":"synthetic-seller","p":100.1,"s":10,"c":[0]},
    ]
    quote_events=[
        {"ev":"Q","sym":"SPY","t":start_ms-2000,"q":1,
         "bp":100,"bs":100,"bx":11,"ap":101,"as":200,"ax":12,
         "c":0,"i":[604]},
        {"ev":"Q","sym":"SPY","t":start_ms+15000,"q":2,
         "bp":100,"bs":100,"bx":11,"ap":101,"as":100,"ax":12,
         "c":0,"i":[604]},
        {"ev":"Q","sym":"SPY","t":start_ms+55000,"q":3,
         "bp":100,"bs":100,"bx":11,"ap":101,"as":190,"ax":12,
         "c":0,"i":[604]},
    ]
    if special_condition is not None:
        quote_events[1]["c"]=special_condition
    groups=[
        [quote_events[0]],[quote_events[1],trades[0]],
        [trades[1]],[quote_events[2]],
    ]
    frames=[]
    for i,group in enumerate(groups):
        received=max(row["t"] for row in group)*1_000_000+1_000_000
        frames.append({"raw_bytes":json.dumps(group).encode(),
                       "frame_received_ns":received,
                       "source_receipt_id":f"synthetic-original-frame-{i}"})
    ref=parse_condition_reference(raw_response_bytes=json.dumps({
        "status":"OK","request_id":"synthetic-conditions",
        "results":[{"asset_class":"stocks","data_types":["trade"],
            "type":"condition","id":0,"name":"Regular Sale",
            "update_rules":{"consolidated":{
                "updates_volume":True,"updates_high_low":True,
                "updates_open_close":True}}}]}).encode(),
        reference_received_ns=start-10_000_000_000,
        source_receipt_id="synthetic-conditions-receipt")
    exchange=parse_exchange_reference(raw_response_bytes=json.dumps({
        "status":"OK","request_id":"synthetic-exchanges",
        "results":[{"asset_class":"stocks","id":11,"type":"exchange"}]}).encode(),
        available_ns=start-10_000_000_000,
        source_receipt_id="synthetic-exchange-receipt")
    policy=parse_quote_policy(original_policy_bytes=json.dumps({
        "schema":QPOLICY_SCHEMA,
        "source_reference_sha256":"c"*64,
        "reviewer_receipt":"synthetic-quote-policy-review",
        "unknown_action":"ABSTAIN",
        "allowed_quote_conditions":[0],"allowed_nbbo_indicators":[604]}).encode(),
        policy_received_ns=start-10_000_000_000,
        policy_receipt_id="synthetic-quote-policy")
    return {
        "original_frames":frames,
        "ticker":"SPY","session":SESSION,"start_ns":start,
        "decision_ns":decision,
        "source_complete_through_ns":end,
        "watermark_available_ns":end+1_000_000_000,
        "watermark_receipt_id":"synthetic-external-source-completeness",
        "source_completeness_attested":True,
        "max_quote_age_ns":25_000_000_000,
        "trade_condition_reference":ref,
        "exchange_reference":exchange,
        "quote_condition_policy":policy,
        "original_reference_custody_attested":True,
    }


class CapturedMinuteIntegrationTests(unittest.TestCase):
    def test_original_frame_batch_reaches_provisional_minute(self):
        args=captured_synthetic_window()
        got=compose_captured_minute(**args)
        self.assertEqual(got["state"],"PRIVATE_SOURCE_CONTEXT_ONLY")
        minute=got["minute_private_only"]
        self.assertEqual(minute["state"],"PROVISIONAL_MEASURED_CONTEXT")
        self.assertEqual(minute["n_sampled_prints"],2)
        self.assertEqual(minute["buy_proxy_notional_usd"],"1009.0")
        self.assertEqual(minute["sell_proxy_notional_usd"],"1001.0")
        self.assertEqual(minute["quote_condition_rules_sha256"],
                         args["quote_condition_policy"]["policy_sha256"])
        self.assertEqual(got["source_frame_count"],4)
        self.assertEqual(got["source_event_count"],5)
        self.assertIsNone(minute["absorption_signal"])
        self.assertEqual(len(got["quote_verdicts_private_memory_only"]),3)
        self.assertEqual(len(got["quotes_private_memory_only"]),3)

    def test_nonfirm_new_quote_blocks_safe_assumption_of_signed_buy(self):
        got=compose_captured_minute(**captured_synthetic_window(special_condition=20))
        minute=got["minute_private_only"]
        self.assertEqual(minute["n_unknown_venue"],0)
        self.assertEqual(minute["n_unclassified"],2)
        self.assertEqual(minute["unknown_notional_usd"],"2010.0")
        from decimal import Decimal
        self.assertEqual(Decimal(minute["sell_proxy_notional_usd"]),Decimal(0))

    def test_external_completeness_missing_yields_no_pseudo_zero_volume(self):
        args=captured_synthetic_window()
        args["source_completeness_attested"]=False
        got=compose_captured_minute(**args)
        self.assertEqual(got["state"],"SOURCE_NOT_QUALIFIED")
        self.assertNotIn("minute_private_only",got)

    def test_external_source_watermark_not_yet_mature(self):
        args=captured_synthetic_window()
        args["source_complete_through_ns"]-=1
        got=compose_captured_minute(**args)
        self.assertEqual(got["state"],"NOT_MATURE")

    def test_source_frame_with_control_event_refused_atomically(self):
        args=captured_synthetic_window()
        args["original_frames"][1]["raw_bytes"]=json.dumps([
            {"ev":"status","status":"auth_success"}]).encode()
        with self.assertRaisesRegex(FrameContractError,"not T or Q"):
            compose_captured_minute(**args)

    def test_source_frame_receipt_must_be_original_and_predecision(self):
        args=captured_synthetic_window()
        args["original_frames"][1]["frame_received_ns"]=args["start_ns"]-10_000_000_000
        with self.assertRaisesRegex(FrameContractError,"precedes vendor SIP"):
            compose_captured_minute(**args)

    def test_captured_quote_stream_has_no_public_publisher(self):
        got=compose_captured_minute(**captured_synthetic_window())
        self.assertIs(got["publication_authority"],False)
        self.assertNotIn("publish_url",got)
        self.assertNotIn("public_r2",got)
        self.assertEqual(got["source_capture_authenticity"],
                         "REQUIRES_ORIGINAL_OWNER_PROOF")

    def test_original_source_digest_set_deterministic(self):
        args=captured_synthetic_window()
        first=compose_captured_minute(**args)
        second=compose_captured_minute(**copy.deepcopy(args))
        self.assertEqual(first["raw_frame_digest_set_sha256"],
                         second["raw_frame_digest_set_sha256"])

    def test_unqualified_reference_custody_cannot_become_signed_minute(self):
        args=captured_synthetic_window()
        args["original_reference_custody_attested"]=False
        got=compose_captured_minute(**args)
        self.assertEqual(got["state"],"SOURCE_NOT_QUALIFIED")
        self.assertNotIn("minute_private_only",got)

if __name__ == "__main__":
    unittest.main()
