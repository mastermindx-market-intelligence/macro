"""Point-in-time provisional trade/quote integration tests."""

import copy
import json
import unittest

from engine.tick_plane.stream_events import normalize_ws_event
from engine.tick_plane.asof_nbbo import InFlightNBBO
from engine.tick_plane.print_observations import observe_provisional_trade

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


def input_args(**updates):
    kw=dict(decision_ns=RECV+20_000_000,
            source_complete_through_ns=(BASE+10)*1_000_000,
            watermark_available_ns=RECV+10,
            watermark_receipt_id="source-owner-contiguous-tq-proof",
            source_completeness_attested=True,
            max_quote_age_ns=50_000_000,
            trade_condition_eligible=True,
            trade_condition_rules_ref="update_rules@source-sha",
            quote_condition_eligible=True,
            quote_condition_rules_ref="quote_conditions@source-sha")
    kw.update(updates)
    return kw


class ProvisionalObservationTests(unittest.TestCase):
    def setUp(self):
        self.ring=InFlightNBBO(session=SESSION,symbols={"SPY"})
        self.ring.ingest_quote(q())

    def observed(self, trade=None, **kw):
        return observe_provisional_trade(t() if trade is None else trade,self.ring,
                                          **input_args(**kw))

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
        r=self.observed(trade_condition_eligible=None)
        self.assertEqual(r["reason"],"TRADE_CONDITION_POLICY_UNQUALIFIED")
        self.assertEqual(r["side_proxy"],"unclassified")

    def test_known_ineligible_condition_does_not_sign_print(self):
        r=self.observed(trade_condition_eligible=False)
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
        r=observe_provisional_trade(t(),ring,**input_args())
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

if __name__ == "__main__":
    unittest.main()
