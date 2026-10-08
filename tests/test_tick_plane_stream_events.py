"""No-network source-normalizer tests (stdlib unittest)."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest

from engine.tick_plane.stream_events import (
    FrameContractError, MAX_FRAME_BYTES, SCHEMA, normalize_ws_event,
)

TIME_MS = 1_728_000_000_000
RECEIVED_NS = TIME_MS * 1_000_000 + 100_000_000
TRADE = {
    "ev": "T", "sym": "SPY", "x": 4, "i": "1234567", "z": 3,
    "p": 573.125, "s": 120, "c": [0, 12], "t": TIME_MS,
    "pt": TIME_MS - 2, "q": 77, "trfi": 201, "trft": TIME_MS - 1,
}
QUOTE = {
    "ev": "Q", "sym": "SPY", "bx": 11, "bp": 573.12, "bs": 100,
    "ax": 12, "ap": 573.13, "as": 200, "c": 0, "i": [604],
    "t": TIME_MS, "pt": TIME_MS - 1, "q": 100, "z": 3,
}


def captured(event, *, index=0, frame=None, **kw):
    if frame is None:
        frame = [event]
    raw = json.dumps(frame, separators=(",", ":")).encode()
    args = dict(raw_frame_bytes=raw, event_index=index,
                frame_received_ns=RECEIVED_NS, source_receipt_id="live-capture:sha256-1",
                session="2026-10-08:RTH", allowed_symbols={"SPY", "QQQ"})
    args.update(kw)
    return normalize_ws_event(**args)


class StreamEventContractTests(unittest.TestCase):
    def test_trade_keeps_original_ms_precision_and_provisional_state(self):
        row = captured(TRADE)
        self.assertEqual(row["schema"], SCHEMA)
        self.assertEqual(row["source_timestamp_precision"], "MILLISECONDS")
        self.assertEqual(row["sip_timestamp_ns"], TIME_MS * 1_000_000)
        self.assertEqual(row["participant_timestamp_ns"], (TIME_MS - 2) * 1_000_000)
        self.assertEqual(row["trf_timestamp_ns"], (TIME_MS - 1) * 1_000_000)
        self.assertEqual(row["original_frame_received_ns"], RECEIVED_NS)
        self.assertEqual(row["correction_status"], "STREAM_PROVISIONAL_UNRECONCILED")
        self.assertIsNone(row["eligible_for_pressure"])
        self.assertIsNone(row["conditions_rules_ref"])
        self.assertEqual(row["trade_action"], "UNRESOLVED_STREAM_ORIGINAL")
        self.assertEqual(row["venue_class"], "TRF")
        self.assertEqual(row["trf_id"], 201)
        self.assertEqual(row["trade_conditions"], [0, 12])
        self.assertEqual(row["price"], "573.125")
        self.assertEqual(row["decimal_size_shares"], "120")

    def test_quote_keeps_order_and_exact_original_frame_receipt(self):
        raw = json.dumps([QUOTE], separators=(",", ":")).encode()
        r = captured(QUOTE)
        self.assertEqual(r["quote_id"], f"2026-10-08:RTH:SPY:Q:100:{TIME_MS*1000000}")
        self.assertEqual(r["source_frame_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertTrue(r["valid_firm_nbbo"])
        self.assertEqual(r["bid"], "573.12")
        self.assertEqual(r["ask"], "573.13")
        self.assertEqual(r["quote_condition"], 0)
        self.assertEqual(r["quote_indicators"], [604])
        self.assertEqual(r["bid_exchange"], 11)
        self.assertEqual(r["ask_exchange"], 12)

    def test_multiple_native_events_get_distinct_event_index_same_frame_digest(self):
        frame = [QUOTE, TRADE]
        a = captured(QUOTE, index=0, frame=frame)
        b = captured(TRADE, index=1, frame=frame)
        self.assertEqual(a["source_frame_sha256"], b["source_frame_sha256"])
        self.assertEqual(a["frame_event_index"], 0)
        self.assertEqual(b["frame_event_index"], 1)
        self.assertEqual(a["event_type"], "Q")
        self.assertEqual(b["event_type"], "T")

    def test_missing_best_side_is_explicit_invalid_quote_not_dropped(self):
        quote = copy.deepcopy(QUOTE)
        for k in ("bp", "bs", "bx"):
            del quote[k]
        q = captured(quote)
        self.assertFalse(q["valid_firm_nbbo"])
        self.assertTrue(q["invalid_nbbo_is_state_not_absent_event"])
        self.assertIsNone(q["bid"])

    def test_missing_quote_sizes_or_zero_best_size_blocks_firm_quote(self):
        for field in ("bs", "as"):
            with self.subTest(field=field):
                quote = copy.deepcopy(QUOTE)
                quote[field] = 0
                self.assertFalse(captured(quote)["valid_firm_nbbo"])

    def test_mismatched_one_sided_quote_fields_rejected(self):
        q = copy.deepcopy(QUOTE)
        del q["bs"]
        with self.assertRaisesRegex(FrameContractError, "mismatched price/size"):
            captured(q)

    def test_locked_and_crossed_quote_remains_invalid_event(self):
        for ask in (573.12, 570):
            with self.subTest(ask=ask):
                q = copy.deepcopy(QUOTE)
                q["ap"] = ask
                self.assertFalse(captured(q)["valid_firm_nbbo"])

    def test_raw_ms_ties_dont_fabricate_ns_trade_quote_order(self):
        t = captured(TRADE)
        q = captured(QUOTE)
        self.assertEqual(t["sip_timestamp_ns"], q["sip_timestamp_ns"])
        self.assertNotIn("quote_id", t)
        self.assertNotIn("trade_id", q)

    def test_fractional_size_even_when_integer_size_is_zero(self):
        t = copy.deepcopy(TRADE)
        t["s"] = 0
        t["ds"] = "0.3725"
        r = captured(t)
        self.assertEqual(r["size_integer_shares"], 0)
        self.assertEqual(r["decimal_size_shares"], "0.3725")
        self.assertIsNone(r["eligible_for_pressure"])

    def test_zero_shares_without_fractional_size_refused(self):
        t = copy.deepcopy(TRADE)
        t["s"] = 0
        with self.assertRaisesRegex(FrameContractError, "zero-size"):
            captured(t)

    def test_quote_sequence_gaps_are_not_declared_missing_source_events(self):
        q = copy.deepcopy(QUOTE)
        q["q"] = 106
        row = captured(q)
        self.assertEqual(row["native_sequence"], 106)
        self.assertNotIn("sequence_gap_detected", row)

    def test_exchange_four_without_trf_is_unknown_not_named_ats(self):
        t = copy.deepcopy(TRADE)
        del t["trfi"]
        self.assertEqual(captured(t)["venue_class"], "UNKNOWN")
        t["x"] = 8
        self.assertEqual(captured(t)["venue_class"], "LIT")

    def test_missing_participant_and_trf_clock_remain_unknown(self):
        t = copy.deepcopy(TRADE)
        t.pop("pt")
        t.pop("trft")
        r = captured(t)
        self.assertIsNone(r["participant_timestamp_ns"])
        self.assertIsNone(r["trf_timestamp_ns"])

    def test_receipt_earlier_than_source_clock_refused(self):
        with self.assertRaisesRegex(FrameContractError, "precedes vendor SIP"):
            captured(QUOTE, frame_received_ns=TIME_MS * 1_000_000 - 1)

    def test_missing_native_source_and_receipt_rejected(self):
        q = copy.deepcopy(QUOTE)
        del q["q"]
        with self.assertRaisesRegex(FrameContractError, "native sequence"):
            captured(q)
        with self.assertRaisesRegex(FrameContractError, "source_receipt_id"):
            captured(QUOTE, source_receipt_id="")

    def test_control_status_messages_are_not_data(self):
        with self.assertRaisesRegex(FrameContractError, "not T or Q"):
            captured({"ev": "status", "status": "auth_success"})

    def test_unsubscribed_symbols_rejected(self):
        q = copy.deepcopy(QUOTE)
        q["sym"] = "NVDA"
        with self.assertRaisesRegex(FrameContractError, "outside the frozen pilot"):
            captured(q)

    def test_unbounded_universe_rejected(self):
        allowed = {"S" + str(x) for x in range(601)}
        with self.assertRaisesRegex(FrameContractError, "unbounded pilot"):
            captured(QUOTE, allowed_symbols=allowed)

    def test_missing_or_malformed_frame_rejected(self):
        cases = [b"", b"null", b"{}", b"{}", b"[", b'{"ev":"T"}']
        for frame in cases:
            with self.subTest(frame=frame), self.assertRaises(FrameContractError):
                captured(QUOTE, raw_frame_bytes=frame)

    def test_duplicate_or_future_index_rejected(self):
        for index in (-1, 1, True):
            with self.subTest(index=index), self.assertRaisesRegex(FrameContractError, "event index"):
                captured(QUOTE, index=index)

    def test_precision_preserves_decimal_not_binary_float_drift(self):
        raw = ('[{"ev":"Q","sym":"SPY","bp":0.1,"bs":10,"bx":1,'
               '"ap":0.3,"as":20,"ax":2,"q":3,"t":'
               + str(TIME_MS) + '}]').encode()
        q = captured(QUOTE, raw_frame_bytes=raw)
        self.assertEqual((q["bid"], q["ask"]), ("0.1", "0.3"))

    def test_invalid_condition_codes_rejected_not_guessed(self):
        t = copy.deepcopy(TRADE)
        t["c"] = [0, True]
        with self.assertRaisesRegex(FrameContractError, "conditions"):
            captured(t)

    def test_unreasonable_frame_size_rejected(self):
        with self.assertRaisesRegex(FrameContractError, "bounded pilot budget"):
            captured(QUOTE, raw_frame_bytes=b" " * (MAX_FRAME_BYTES + 1))

    def test_source_event_order_does_not_imply_corrections_resolved(self):
        t = copy.deepcopy(TRADE)
        t["q"] = 200
        r = captured(t)
        self.assertEqual(r["correction_status"], "STREAM_PROVISIONAL_UNRECONCILED")
        self.assertFalse(r["eligible_for_pressure"] is True)


if __name__ == "__main__":
    unittest.main()


    def test_trade_identity_scoped_by_exchange_and_trf(self):
        a = copy.deepcopy(TRADE)
        b = copy.deepcopy(TRADE)
        b["x"] = 11
        b.pop("trfi", None)
        self.assertNotEqual(captured(a)["dedup_key"], captured(b)["dedup_key"])
        c = copy.deepcopy(TRADE)
        c["trfi"] = 202
        self.assertNotEqual(captured(a)["dedup_key"], captured(c)["dedup_key"])
