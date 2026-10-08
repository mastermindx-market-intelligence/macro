"""Point-in-time provisional trade/quote integration tests."""

import copy
import json
import unittest

from engine.tick_plane.stream_events import normalize_ws_event
from engine.tick_plane.asof_nbbo import InFlightNBBO
from engine.tick_plane.print_observations import observe_provisional_trade
from engine.tick_plane.condition_policy import parse_condition_reference, evaluate_trade_conditions

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
       "bs":100,"ax":2,"ap":100.2,"as":200}
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


def input_args(trade=None,**updates):
    trade = t() if trade is None else trade
    kw=dict(decision_ns=RECV+20_000_000,
            source_complete_through_ns=(BASE+10)*1_000_000,
            watermark_available_ns=RECV+10,
            watermark_receipt_id="source-owner-contiguous-tq-proof",
            source_completeness_attested=True,
            max_quote_age_ns=50_000_000,
            trade_condition_verdict=condition_verdict(trade),
            quote_condition_eligible=True,
            quote_condition_rules_ref="quote_conditions@source-sha")
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
        r=self.observed(quote_condition_eligible=None)
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


if __name__ == "__main__":
    unittest.main()
