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
    def test_invalid_json_numeric_exponent_or_integer_has_typed_source_failure(self):
        from engine.tick_plane.stream_events import normalize_ws_event
        original = json.dumps([TRADE]).encode()
        inputs = [
            original.replace(b"573.125", b"1e999999999999999999999999999"),
            original.replace(b'"q": 77', b'"q": ' + b"9" * 5000),
        ]
        for raw in inputs:
            with self.subTest(raw_size=len(raw)):
                with self.assertRaisesRegex(FrameContractError, "invalid original UTF-8 JSON frame"):
                    normalize_ws_event(raw, event_index=0, frame_received_ns=RECEIVED_NS,
                                       source_receipt_id="original-probe", session="2026-10-08:RTH",
                                       allowed_symbols={"SPY"})

    def test_scientific_exponents_do_not_expand_into_unbounded_fixed_strings(self):
        from engine.tick_plane.stream_events import normalize_ws_event, _decimal
        for exponent in ("1e+999999999", "1e-999999999"):
            # Native JSON floats use parse_float=Decimal and need the same bound.
            raw = json.dumps([TRADE]).encode().replace(b"573.125", exponent.encode())
            with self.subTest(transport="native", exponent=exponent):
                with self.assertRaisesRegex(FrameContractError, "fixed decimal exceeds"):
                    normalize_ws_event(raw, event_index=0, frame_received_ns=RECEIVED_NS,
                                       source_receipt_id="original-probe", session="2026-10-08:RTH",
                                       allowed_symbols={"SPY"})
            for field in ("p", "ds"):
                trade = dict(TRADE, **{field: exponent})
                with self.subTest(transport="string", field=field, exponent=exponent):
                    with self.assertRaisesRegex(FrameContractError, "fixed decimal exceeds"):
                        captured(trade)
            quote = dict(QUOTE, bp=exponent)
            with self.subTest(transport="quote", exponent=exponent):
                with self.assertRaisesRegex(FrameContractError, "fixed decimal exceeds"):
                    captured(quote)
        self.assertEqual(_decimal("0.125", "shares"), "0.125")
        self.assertEqual(len(_decimal("1e+125", "price")), 126)

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




    def test_trade_identity_scoped_by_exchange_and_trf(self):
        a = copy.deepcopy(TRADE)
        b = copy.deepcopy(TRADE)
        b["x"] = 11
        b.pop("trfi", None)
        self.assertNotEqual(captured(a)["dedup_key"], captured(b)["dedup_key"])
        c = copy.deepcopy(TRADE)
        c["trfi"] = 202
        self.assertNotEqual(captured(a)["dedup_key"], captured(c)["dedup_key"])


    def test_fractional_size_must_agree_with_vendor_integer_floor(self):
        bad = copy.deepcopy(TRADE)
        bad["s"] = 10
        bad["ds"] = "12.5"
        with self.assertRaisesRegex(FrameContractError, "disagrees"):
            captured(bad)
        good = copy.deepcopy(TRADE)
        good["s"] = 10
        good["ds"] = "10.875"
        self.assertEqual(captured(good)["decimal_size_shares"], "10.875")


    def test_finra_orf_and_sip_codes_never_masquerade_as_lit(self):
        for exchange in (5, 13, 62):
            with self.subTest(exchange=exchange):
                record = copy.deepcopy(TRADE)
                record["x"] = exchange
                record.pop("trfi", None)
                parsed = captured(record)
                self.assertEqual(parsed["venue_class"], "UNKNOWN")
                self.assertEqual(parsed["exchange"], exchange)

    def test_unknown_trf_pipe_does_not_gain_named_facility_authority(self):
        record = copy.deepcopy(TRADE)
        record["x"] = 4
        record["trfi"] = 999
        self.assertEqual(captured(record)["venue_class"], "UNKNOWN")

    def test_known_trf_codes_are_reporting_facility_not_lit(self):
        for code in (201, 202, 203):
            record = copy.deepcopy(TRADE)
            record["x"] = 4
            record["trfi"] = code
            self.assertEqual(captured(record)["venue_class"], "TRF")


from engine.tick_plane.exchange_reference import (
    parse_exchange_reference, classify_trade_venue, FrameContractError as VenueError,
)


def exchange_ref(*, received=RECEIVED_NS-1000, rows=None):
    if rows is None:
        rows=[{"asset_class":"stocks","id":11,"type":"exchange"},
              {"asset_class":"stocks","id":4,"type":"TRF"},
              {"asset_class":"stocks","id":5,"type":"SIP"},
              {"asset_class":"stocks","id":13,"type":"SIP"},
              {"asset_class":"stocks","id":62,"type":"TRF"}]
    raw=json.dumps({"status":"OK","request_id":"exchange-native-reference",
                    "results":rows}).encode()
    return parse_exchange_reference(raw_response_bytes=raw,
           available_ns=received,source_receipt_id="original-exchange-reference")


def venue(trade=None, reference=None, **kw):
    t=captured(TRADE if trade is None else trade)
    ref=exchange_ref() if reference is None else reference
    args=dict(trade=t,reference=ref,decision_ns=RECEIVED_NS+2000,
              original_reference_custody_attested=True)
    args.update(kw)
    return classify_trade_venue(**args)


class OriginalExchangeReferenceTests(unittest.TestCase):
    def test_reference_admits_only_known_native_exchange(self):
        trade=copy.deepcopy(TRADE)
        trade["x"]=11
        trade.pop("trfi",None)
        result=venue(trade)
        self.assertEqual(result["venue_class"],"LIT")
        self.assertTrue(result["lit_eligible"])
        self.assertEqual(result["authority"],"VENUE_OBSERVATION_ONLY")
        self.assertEqual(len(result["exchange_reference_sha256"]),64)

    def test_named_trf_pipe_is_reporting_route_not_dark_pool_identity(self):
        result=venue()
        self.assertEqual(result["venue_class"],"TRF")
        self.assertFalse(result["lit_eligible"])
        self.assertIn("NOT_NAMED_ATS",result["reason"])

    def test_orf_and_sip_remain_unknown_even_with_reference(self):
        for exchange in (5,13,62):
            record=copy.deepcopy(TRADE)
            record["x"]=exchange
            record.pop("trfi",None)
            with self.subTest(exchange=exchange):
                self.assertEqual(venue(record)["venue_class"],"UNKNOWN")

    def test_unknown_exchange_never_assumes_lit(self):
        tr=copy.deepcopy(TRADE)
        tr["x"]=999
        tr.pop("trfi",None)
        self.assertEqual(venue(tr)["reason"],"EXCHANGE_MISSING_IN_REFERENCE")

    def test_unrecognized_trf_code_cannot_be_lit(self):
        tr=copy.deepcopy(TRADE)
        tr["trfi"]=999
        self.assertEqual(venue(tr)["venue_class"],"UNKNOWN")

    def test_reference_after_decision_cannot_backfill(self):
        late=exchange_ref(received=RECEIVED_NS+100000)
        got=venue(reference=late)
        self.assertEqual(got["reason"],"REFERENCE_OR_TRADE_NOT_KNOWN_AT_DECISION")

    def test_unattested_reference_never_admits_lit(self):
        tr=copy.deepcopy(TRADE);tr["x"]=11;tr.pop("trfi",None)
        self.assertEqual(venue(tr,original_reference_custody_attested=False)["venue_class"],"UNKNOWN")

    def test_trade_arriving_after_decision_abstains(self):
        tr=captured(TRADE)
        tr["original_frame_received_ns"]=RECEIVED_NS+500000
        result=classify_trade_venue(trade=tr,reference=exchange_ref(),
                                    decision_ns=RECEIVED_NS+1000,
                                    original_reference_custody_attested=True)
        self.assertEqual(result["reason"],"REFERENCE_OR_TRADE_NOT_KNOWN_AT_DECISION")

    def test_source_type_conflict_cannot_relabel_orf_as_exchange(self):
        recs=[{"asset_class":"stocks","id":62,"type":"exchange"}]
        ref=exchange_ref(rows=recs)
        tr=copy.deepcopy(TRADE);tr["x"]=62;tr.pop("trfi",None)
        self.assertEqual(venue(tr,reference=ref)["reason"],"NONLIT_SOURCE_TYPE_CONFLICT")

    def test_duplicated_conflicting_exchange_id_refused(self):
        recs=[{"asset_class":"stocks","id":11,"type":"exchange"},
              {"asset_class":"stocks","id":11,"type":"TRF"}]
        with self.assertRaisesRegex(FrameContractError,"conflicting exchange"):
            exchange_ref(rows=recs)

    def test_bad_venue_reference_not_treated_as_empty(self):
        with self.assertRaisesRegex(FrameContractError,"stock exchange reference"):
            exchange_ref(rows=[{"asset_class":"options","id":11,"type":"exchange"}])

    def test_invalid_venue_reference_type_fails_closed(self):
        with self.assertRaisesRegex(FrameContractError,"unknown reference venue"):
            exchange_ref(rows=[{"asset_class":"stocks","id":11,"type":"otc"}])

from engine.tick_plane.stream_events import normalize_ws_frame, MAX_FRAME_EVENTS


class BatchedOriginalFrameTests(unittest.TestCase):
    def frame(self, rows):
        return json.dumps(rows,separators=(",",":")).encode()

    def decode(self, rows, **other):
        frame=self.frame(rows)
        args={"raw_frame_bytes":frame,"frame_received_ns":RECEIVED_NS,
              "source_receipt_id":"original:batch:receipt",
              "session":"2026-10-08:RTH","allowed_symbols":{"SPY"}}
        args.update(other)
        return normalize_ws_frame(**args)

    def test_batch_byte_identical_to_single_event_normalizer(self):
        values=[QUOTE,TRADE]
        results=self.decode(values)
        frame=self.frame(values)
        for i,expected in enumerate(results):
            other=normalize_ws_event(frame,event_index=i,
                    frame_received_ns=RECEIVED_NS,source_receipt_id="original:batch:receipt",
                    session="2026-10-08:RTH",allowed_symbols={"SPY"})
            self.assertEqual(expected,other)
        self.assertEqual(results[0]["frame_event_index"],0)
        self.assertEqual(results[1]["frame_event_index"],1)
        self.assertEqual(results[0]["source_frame_sha256"],results[1]["source_frame_sha256"])

    def test_batch_parses_original_json_exactly_once(self):
        from unittest.mock import patch
        from engine.tick_plane import stream_events
        with patch.object(stream_events.json, "loads", wraps=stream_events.json.loads) as loader:
            frame=self.decode([QUOTE,TRADE,QUOTE])
        self.assertEqual(loader.call_count,1)
        self.assertEqual(len(frame),3)

    def test_full_batch_refuses_mixed_status_control_frames(self):
        values=[QUOTE,{"ev":"status","status":"auth_success"},TRADE]
        with self.assertRaisesRegex(FrameContractError,"not T or Q"):
            self.decode(values)

    def test_full_batch_refuses_invalid_out_of_universe_row(self):
        bad=copy.deepcopy(TRADE)
        bad["sym"]="AAPL"
        with self.assertRaisesRegex(FrameContractError,"outside the frozen pilot"):
            self.decode([QUOTE,bad])

    def test_bad_event_clock_refuses_whole_frame(self):
        bad=copy.deepcopy(TRADE)
        bad["t"]=TIME_MS+99999
        with self.assertRaisesRegex(FrameContractError,"precedes vendor SIP"):
            self.decode([QUOTE,bad])

    def test_empty_and_nonlist_batch_are_not_valid_data(self):
        for raw in (b"[]",b"{}",b"null",b""):
            with self.subTest(raw=raw),self.assertRaises(FrameContractError):
                normalize_ws_frame(raw,frame_received_ns=RECEIVED_NS,
                        source_receipt_id="fixture",session="2026-10-08:RTH",
                        allowed_symbols={"SPY"})

    def test_bounded_frame_event_count_enforced(self):
        many=[QUOTE]*(MAX_FRAME_EVENTS+1)
        with self.assertRaisesRegex(FrameContractError,"bounded event budget"):
            self.decode(many)

    def test_batch_allows_multiple_same_ms_without_invented_order(self):
        events=[QUOTE,copy.deepcopy(QUOTE)]
        events[1]["q"]=101
        batch=self.decode(events)
        self.assertEqual(batch[0]["sip_timestamp_ns"],batch[1]["sip_timestamp_ns"])
        self.assertEqual([r["frame_event_index"] for r in batch],[0,1])
        self.assertNotIn("trade_aggressor_truth",str(batch))

    def test_batch_precise_decimal_price_and_fractional_size(self):
        tr=copy.deepcopy(TRADE)
        tr["p"]=100.125
        tr["s"]=0
        tr["ds"]="0.375"
        batch=self.decode([tr])
        self.assertEqual(batch[0]["price"],"100.125")
        self.assertEqual(batch[0]["decimal_size_shares"],"0.375")
        self.assertEqual(batch[0]["correction_status"],
                         "STREAM_PROVISIONAL_UNRECONCILED")

    def test_batch_does_not_change_market_tape_status_on_error(self):
        with self.assertRaises(FrameContractError):
            self.decode([QUOTE,{"ev":"X","sym":"SPY"}])
        self.assertEqual(len(self.decode([QUOTE])),1)

if __name__ == "__main__":
    unittest.main()
