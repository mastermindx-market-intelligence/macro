"""Hermetic, stdlib-only tests for a source-attested as-of quote ring."""
import copy
import json
import unittest

from engine.tick_plane.stream_events import normalize_ws_event, FrameContractError
from engine.tick_plane.asof_nbbo import InFlightNBBO

BASE = 1_791_417_600_000
INGEST = BASE * 1_000_000 + 200_000_000
S = "2026-10-08:RTH"


def source(event):
    b = json.dumps([event]).encode()
    return normalize_ws_event(b, event_index=0, frame_received_ns=INGEST,
                              source_receipt_id="frame-capture-verified-by-owner",
                              session=S, allowed_symbols={"SPY", "QQQ"})


def quote(seq, when, **changes):
    row = {"ev":"Q","sym":"SPY","t":when,"q":seq,"bp":100.1,"bs":50,
           "bx":1,"ap":100.2,"as":70,"ax":2,"z":3}
    row.update(changes)
    return source(row)


def trade(when, **changes):
    row = {"ev":"T","sym":"SPY","t":when,"q":999,"i":"T1",
           "p":100.2,"s":100,"x":1,"z":3}
    row.update(changes)
    return source(row)


def opts(**kwargs):
    base = dict(decision_ns=INGEST+10_000_000,
                source_complete_through_ns=(BASE+300)*1_000_000,
                watermark_available_ns=INGEST+1,
                watermark_receipt_id="joint-tq-completeness-owner-receipt",
                source_completeness_attested=True,
                max_quote_age_ns=1_000_000_000,
                quote_condition_eligible=True,
                quote_condition_rules_ref="ref/quote-conditions@sha")
    base.update(kwargs)
    return base


class NBBOAsOfTests(unittest.TestCase):
    def setUp(self):
        self.ring=InFlightNBBO(session=S,symbols={"SPY", "QQQ"},per_symbol_cap=8)
        self.q=quote(1,BASE)
        self.t=trade(BASE+20)
        self.ring.ingest_quote(self.q)

    def test_known_prior_nbbo_returns_original_receipt(self):
        o=self.ring.match(self.t,**opts())
        self.assertEqual(o["state"],"MATCHED_SOURCE_CONTEXT")
        self.assertEqual(o["quote"]["source_frame_sha256"],self.q["source_frame_sha256"])
        self.assertEqual(o["quote_age_ns"],20_000_000)
        self.assertEqual(o["authority"],"SOURCE_CONTEXT_ONLY")

    def test_same_millisecond_trade_quote_abstains(self):
        self.ring.ingest_quote(quote(2,BASE+20))
        self.assertEqual(self.ring.match(self.t,**opts())["reason"],"UNORDERED_SAME_MILLISECOND")

    def test_quote_observed_after_decision_cannot_replace_old_quote(self):
        q2=quote(2,BASE+10)
        q2["original_frame_received_ns"]=INGEST+100_000_000
        self.ring.ingest_quote(q2)
        o=self.ring.match(self.t,**opts())
        self.assertEqual(o["quote"]["native_sequence"],1)

    def test_invalid_one_sided_update_blocks_older_quote(self):
        q2=quote(2,BASE+10, bp=None,bs=None,bx=None)
        self.ring.ingest_quote(q2)
        self.assertEqual(self.ring.match(self.t,**opts())["reason"],"INVALID_OR_ONE_SIDED_NBBO")

    def test_stale_quote_abstains(self):
        o=self.ring.match(self.t,**opts(max_quote_age_ns=5_000_000))
        self.assertEqual(o["reason"],"QUOTE_STALE")

    def test_unattested_watermark_abstains(self):
        self.assertEqual(self.ring.match(self.t,**opts(source_completeness_attested=False))["reason"],
                         "SOURCE_COMPLETENESS_UNATTESTED")

    def test_future_watermark_receipt_abstains(self):
        self.assertEqual(self.ring.match(self.t,**opts(watermark_available_ns=INGEST+20_000_000))["reason"],
                         "WATERMARK_NOT_KNOWABLE")

    def test_unmatured_trade_event_abstains(self):
        self.assertEqual(self.ring.match(self.t,**opts(source_complete_through_ns=BASE*1_000_000))["reason"],
                         "TRADE_WINDOW_NOT_COMPLETE")

    def test_quote_conditions_are_not_assumed(self):
        self.assertEqual(self.ring.match(self.t,**opts(quote_condition_eligible=None))["reason"],
                         "QUOTE_CONDITION_POLICY_UNQUALIFIED")

    def test_quote_sequence_nonconsecutive_is_not_a_gap(self):
        self.ring.ingest_quote(quote(9,BASE+10))
        self.assertEqual(self.ring.match(self.t,**opts())["quote"]["native_sequence"],9)

    def test_same_quote_duplicate_is_idempotent(self):
        self.assertFalse(self.ring.ingest_quote(copy.deepcopy(self.q)))
        self.assertEqual(self.ring.match(self.t,**opts())["state"],"MATCHED_SOURCE_CONTEXT")

    def test_conflicting_native_sequence_poisoned(self):
        with self.assertRaisesRegex(FrameContractError,"conflicting native"):
            self.ring.ingest_quote(quote(1,BASE+10))
        self.assertEqual(self.ring.match(self.t,**opts())["reason"],"SOURCE_GAP_QUARANTINED")

    def test_explicit_gap_stays_fenced_after_new_quote(self):
        self.ring.mark_gap("SPY")
        with self.assertRaisesRegex(FrameContractError,"gap fence"):
            self.ring.ingest_quote(quote(2,BASE+10))
        self.assertEqual(self.ring.match(self.t,**opts())["reason"],"SOURCE_GAP_QUARANTINED")

    def test_invalid_quote_session_rejected(self):
        q=copy.deepcopy(self.q)
        q["session"]="2026-10-07:RTH"
        with self.assertRaisesRegex(FrameContractError,"session"):
            self.ring.ingest_quote(q)

    def test_invalid_quote_type_rejected(self):
        with self.assertRaisesRegex(FrameContractError,"only normalized native quotes"):
            self.ring.ingest_quote(self.t)

    def test_memory_ring_cap_is_bounded(self):
        r=InFlightNBBO(session=S,symbols={"SPY"},per_symbol_cap=2)
        for seq in range(1,5):
            r.ingest_quote(quote(seq,BASE+seq))
        self.assertEqual(r.match(trade(BASE+10),**opts())["ring_dropped_old_updates"],2)

    def test_never_mutates_captured_quote(self):
        o=self.ring.match(self.t,**opts())
        o["quote"]["ask"]="0"
        self.assertEqual(self.ring.match(self.t,**opts())["quote"]["ask"],"100.2")

    def test_cross_symbol_trade_is_unknown(self):
        t=copy.deepcopy(self.t)
        t["ticker"]="NVDA"
        self.assertEqual(self.ring.match(t,**opts())["reason"],"SESSION_OR_TICKER_MISMATCH")

    def test_trade_receipt_after_decision_abstains(self):
        t=copy.deepcopy(self.t)
        t["original_frame_received_ns"]=INGEST+50_000_000
        self.assertEqual(self.ring.match(t,**opts())["reason"],"TRADE_NOT_AVAILABLE_AT_DECISION")

    def test_session_scoped_quote_ring_rejects_infinite_cap(self):
        with self.assertRaisesRegex(FrameContractError,"bounded maximum"):
            InFlightNBBO(session=S,symbols={"SPY"},per_symbol_cap=10_000)

if __name__ == "__main__":
    unittest.main()
