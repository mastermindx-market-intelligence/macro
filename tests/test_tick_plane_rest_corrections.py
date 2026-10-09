"""Unittest fixtures for corrections without retroactive historical leakage."""

import copy
import hashlib
import json
import unittest

from engine.tick_plane.stream_events import normalize_ws_event, FrameContractError
from engine.tick_plane.rest_corrections import compare_rest_trade

TMS = 1_791_417_600_000
SEEN = TMS * 1_000_000 + 200_000_000
WS = {"ev":"T","sym":"SPY","x":4,"trfi":201,"i":"123","z":3,
      "p":100.25,"s":10,"q":11,"t":TMS,"c":[0]}


def ws(**changes):
    row=copy.deepcopy(WS)
    row.update(changes)
    return normalize_ws_event(
        json.dumps([row]).encode(),event_index=0,
        frame_received_ns=SEEN,source_receipt_id="stream-original-capture",
        session="2026-10-08:RTH",allowed_symbols={"SPY"})


def rest_row(**changes):
    row={"id":"123","exchange":4,"trf_id":201,
         "sip_timestamp":TMS*1_000_000+123_456,
         "price":100.25,"size":10,"decimal_size":"10","correction":0}
    row.update(changes)
    return row


def compare(trade=None, rows=None, **kwargs):
    raw=json.dumps({"status":"OK","request_id":"req-aa",
                    "results":[rest_row()] if rows is None else rows}).encode()
    args={"stream_trade":ws() if trade is None else trade,
          "raw_rest_bytes":raw,"fetched_at_ns":SEEN+10_000_000,
          "source_receipt_id":"rest-retrieved-generation-1",
          "requested_ticker":"SPY"}
    args.update(kwargs)
    return compare_rest_trade(**args)


class CorrectionComparisonTests(unittest.TestCase):
    def test_matching_rest_is_only_a_current_vintage_observation(self):
        a=compare()
        self.assertEqual(a["state"],"MATCHED_CURRENT_REST_VINTAGE_NOT_AS_SEEN")
        self.assertEqual(a["stream_reconciliation_state"],"PROVISIONAL_UNCHANGED")
        self.assertEqual(a["stream_original_available_ns"],SEEN)
        self.assertEqual(a["rest_available_ns"],SEEN+10_000_000)
        self.assertEqual(a["authority"],"RESEARCH_CONTEXT_ONLY")
        self.assertEqual(a["rest_correction_code"],0)

    def test_no_rest_row_is_not_automatic_cancel(self):
        a=compare(rows=[])
        self.assertEqual(a["state"],"NOT_IN_REST_SAMPLE_UNKNOWN")
        self.assertEqual(a["stream_reconciliation_state"],"PROVISIONAL_UNCHANGED")

    def test_corrected_cancelled_or_nonzero_codes_quarantined(self):
        for code in (1,8,10,11,12,999):
            with self.subTest(code=code):
                self.assertEqual(compare(rows=[rest_row(correction=code)])["state"],
                                 "CORRECTION_FLAG_PRESENT_NEEDS_NATIVE_LINEAGE")

    def test_ambiguous_correction_versions_do_not_select_latest(self):
        a=compare(rows=[rest_row(correction=8),rest_row(correction=10)])
        self.assertEqual(a["state"],"MULTIPLE_NATIVE_REST_GENERATIONS_NEED_LINEAGE")

    def test_rest_query_must_be_completely_paginated(self):
        raw=json.dumps({"status":"OK","request_id":"x","results":[rest_row()],
                        "next_url":"https://api.massive.com/continuation"}).encode()
        self.assertEqual(compare(raw_rest_bytes=raw)["state"],"PAGINATION_INCOMPLETE")

    def test_id_collision_different_exchange_not_misjoined(self):
        a=compare(rows=[rest_row(exchange=11)])
        self.assertEqual(a["state"],"NOT_IN_REST_SAMPLE_UNKNOWN")

    def test_id_collision_different_trf_not_misjoined(self):
        a=compare(rows=[rest_row(trf_id=202)])
        self.assertEqual(a["state"],"NOT_IN_REST_SAMPLE_UNKNOWN")

    def test_exchange_matches_but_timestamp_ms_differs(self):
        a=compare(rows=[rest_row(sip_timestamp=(TMS+1)*1_000_000)])
        self.assertEqual(a["state"],"SIP_TIME_SCOPE_DISAGREEMENT")

    def test_price_revision_does_not_rewrite_original(self):
        a=compare(rows=[rest_row(price=100.5)])
        self.assertEqual(a["state"],"REST_PRICE_RESTATED_UNLINKED")
        self.assertEqual(a["stream_reconciliation_state"],"PROVISIONAL_UNCHANGED")

    def test_size_revision_requires_original_lineage(self):
        a=compare(rows=[rest_row(decimal_size="11")])
        self.assertEqual(a["state"],"REST_SIZE_RESTATED_UNLINKED")

    def test_missing_optional_correction_does_not_prove_finality(self):
        row=rest_row()
        del row["correction"]
        a=compare(rows=[row])
        self.assertEqual(a["state"],"MATCHED_CURRENT_REST_VINTAGE_NOT_AS_SEEN")
        self.assertIsNone(a["rest_correction_code"])

    def test_identical_trade_id_different_exchanges_have_distinct_native_keys(self):
        first=ws()
        second=ws(x=11,trfi=None)
        self.assertNotEqual(first["dedup_key"],second["dedup_key"])

    def test_rest_receipt_bytes_digest_is_bound(self):
        raw=json.dumps({"status":"OK","request_id":"req-aa","results":[rest_row()]}).encode()
        a=compare(raw_rest_bytes=raw)
        self.assertEqual(a["rest_response_sha256"],hashlib.sha256(raw).hexdigest())

    def test_rest_receipt_cannot_predate_websocket_observation(self):
        with self.assertRaisesRegex(FrameContractError,"predates"):
            compare(fetched_at_ns=SEEN-1)

    def test_required_requested_ticker_match(self):
        with self.assertRaisesRegex(FrameContractError,"ticker"):
            compare(requested_ticker="QQQ")

    def test_rest_query_empty_provenance_is_not_accepted(self):
        for packet in ({},{"status":"OK","results":[]},
                       {"status":"OK","request_id":"x","results":None}):
            with self.subTest(packet=packet),self.assertRaises(FrameContractError):
                compare(raw_rest_bytes=json.dumps(packet).encode())

    def test_rest_malformed_bytes_refused(self):
        with self.assertRaises(FrameContractError):
            compare(raw_rest_bytes=b"{")

    def test_not_a_stream_trade_refused(self):
        t=ws()
        t["event_type"]="Q"
        with self.assertRaises(FrameContractError):
            compare(trade=t)

    def test_missing_correction_authority_cannot_be_issued_by_this_comparison(self):
        a=compare()
        self.assertNotIn("finalized",a)
        self.assertNotIn("trade_action",a)


from engine.tick_plane.rest_page import normalize_rest_page

REST_START = TMS * 1_000_000
REST_END = REST_START + 60_000_000_000
REST_RECEIVED = REST_END + 1_000_000_000


def historical(kind, rows, **changes):
    response = {"status": "OK", "request_id": "historical-r1",
                "results": rows}
    raw = json.dumps(response).encode()
    kw = {"raw_bytes": raw, "endpoint_kind": kind, "ticker": "SPY",
          "session": "2026-10-08:RTH", "window_start_ns": REST_START,
          "window_end_ns": REST_END, "page_received_ns": REST_RECEIVED,
          "original_page_receipt": "original-bytes:sha256"}
    kw.update(changes)
    return normalize_rest_page(**kw)


class HistoricalRestPageTests(unittest.TestCase):
    def quote(self, **changes):
        row = {"sip_timestamp": REST_START + 123, "sequence_number": 77,
               "bid_exchange": 11, "bid_price": 102.7, "bid_size": 60,
               "ask_exchange": 0, "ask_price": 0, "ask_size": 0,
               "conditions": [1], "participant_timestamp": REST_START + 120,
               "tape": 3}
        row.update(changes)
        return row

    def trade(self, **changes):
        row = {"sip_timestamp": REST_START + 456, "sequence_number": 65,
               "exchange": 11, "id": "R1", "price": 171.55,
               "size": 100, "decimal_size": "100.0",
               "conditions": [12, 41], "participant_timestamp": REST_START + 454}
        row.update(changes)
        return row

    def test_exact_nanosecond_quote_and_one_sided_condition(self):
        p = historical("quotes", [self.quote()])
        q = p["private_rows"][0]
        self.assertEqual(q["sip_timestamp_ns"], REST_START + 123)
        self.assertEqual(q["original_available_ns"], REST_RECEIVED)
        self.assertFalse(q["valid_firm_nbbo_candidate"])
        self.assertEqual(q["bid"], "102.7")
        self.assertEqual(q["ask"], "0")
        self.assertEqual(q["conditions"], [1])
        self.assertIsNone(q["quote_condition_eligibility"])
        self.assertEqual(p["evidence_mode"], "FINAL_VINTAGE")
        self.assertIsNone(p["total_range_complete"])

    def test_two_sided_quote_eligible_candidate_not_signed(self):
        p = historical("quotes", [self.quote(ask_exchange=4,
                           ask_price=102.72, ask_size=100)])
        q = p["private_rows"][0]
        self.assertTrue(q["valid_firm_nbbo_candidate"])
        self.assertIsNone(q["quote_condition_eligibility"])

    def test_native_trade_id_scoped_to_exchange_trf(self):
        a = historical("trades", [self.trade()])["private_rows"][0]
        b = historical("trades", [self.trade(exchange=4, trf_id=201)])["private_rows"][0]
        self.assertNotEqual(a["native_key"], b["native_key"])
        self.assertEqual(b["venue_class"], "TRF")

    def test_retroactive_correction_stays_unlinked(self):
        q = historical("trades", [self.trade(correction=8)])["private_rows"][0]
        self.assertEqual(q["correction_status"], "CORRECTION_PRESENT_UNLINKED")
        self.assertIsNone(q["eligible_for_pressure"])

    def test_zero_correction_not_as_seen_or_final(self):
        q = historical("trades", [self.trade(correction=0)])["private_rows"][0]
        self.assertEqual(q["correction_status"], "CURRENT_VINTAGE_NOT_HISTORICALLY_FINAL")
        self.assertEqual(q["mode"], "FINAL_VINTAGE_NOT_AS_SEEN")

    def test_fractional_size_preserves_decimal(self):
        q = historical("trades", [self.trade(size=0, decimal_size="0.125")])["private_rows"][0]
        self.assertEqual(q["decimal_size_shares"], "0.125")

    def test_integer_decimal_size_inconsistency_refused(self):
        with self.assertRaisesRegex(FrameContractError, "disagree"):
            historical("trades", [self.trade(size=101)])

    def test_missing_conditions_are_unknown_not_empty(self):
        row = self.trade()
        row.pop("conditions")
        q = historical("trades", [row])["private_rows"][0]
        self.assertIsNone(q["conditions"])

    def test_pagination_never_claims_complete_history(self):
        p = historical("quotes", [self.quote()])
        self.assertEqual(p["pagination"], "TERMINAL_PAGE_NOT_COVERAGE_PROOF")
        self.assertIsNone(p["market_capture_coverage"])

    def test_next_url_is_not_persisted_even_in_diagnostics(self):
        link = "https://api.massive.com/v3/quotes/SPY?cursor=SENSITIVE"
        packet = json.dumps({"status": "OK", "request_id": "historical-r1",
                             "results": [self.quote()], "next_url": link}).encode()
        r = historical("quotes", [self.quote()], raw_bytes=packet)
        self.assertEqual(r["pagination"], "MORE_PAGES_REQUIRED")
        self.assertNotIn("SENSITIVE", json.dumps(r))

    def test_original_response_digest_is_byte_exact(self):
        packet = json.dumps({"status": "OK", "request_id": "historical-r1",
                             "results": [self.trade()]}).encode()
        r = historical("trades", [self.trade()], raw_bytes=packet)
        self.assertEqual(r["source_sha256"], hashlib.sha256(packet).hexdigest())

    def test_out_of_range_cannot_count_toward_window(self):
        with self.assertRaisesRegex(FrameContractError, "outside requested"):
            historical("quotes", [self.quote(sip_timestamp=REST_END)])

    def test_receipt_after_query_end_required(self):
        with self.assertRaisesRegex(FrameContractError, "availability timestamp"):
            historical("quotes", [self.quote()], page_received_ns=REST_END-1)

    def test_duplicate_trade_identity_requires_adjudication(self):
        with self.assertRaisesRegex(FrameContractError, "duplicate native identity"):
            historical("trades", [self.trade(), self.trade(correction=8)])

    def test_quote_native_sequence_duplicate_requires_adjudication(self):
        with self.assertRaisesRegex(FrameContractError, "duplicate native identity"):
            historical("quotes", [self.quote(), self.quote()])

    def test_floating_nanosecond_clock_rejected_not_rounded(self):
        with self.assertRaisesRegex(FrameContractError, "sip_timestamp"):
            historical("quotes", [self.quote(sip_timestamp=float(REST_START+123))])

    def test_malformed_page_and_missing_source_receipt_fail_closed(self):
        with self.assertRaises(FrameContractError):
            historical("quotes", [self.quote()], raw_bytes=b"{")
        with self.assertRaises(FrameContractError):
            historical("quotes", [self.quote()], original_page_receipt="")

    def test_zero_quote_size_and_partial_sides_remain_nonfirm(self):
        q = self.quote()
        q.pop("ask_price")
        q.pop("ask_size")
        self.assertFalse(historical("quotes", [q])["private_rows"][0]["valid_firm_nbbo_candidate"])

    def test_rest_page_limit_enforced(self):
        from engine.tick_plane.rest_page import MAX_PAGE_BYTES
        with self.assertRaisesRegex(FrameContractError, "oversized"):
            historical("quotes", [self.quote()], raw_bytes=b"x" * (MAX_PAGE_BYTES+1))

    def test_noninteger_firm_size_stays_nonfirm(self):
        q = self.quote(ask_price=102.72, ask_exchange=4, ask_size=1.25)
        self.assertFalse(historical("quotes", [q])["private_rows"][0]["valid_firm_nbbo_candidate"])

    def test_historical_orf_and_sip_not_lit(self):
        for exchange in (5, 13, 62):
            with self.subTest(exchange=exchange):
                record = self.trade(exchange=exchange)
                output = historical("trades", [record])["private_rows"][0]
                self.assertEqual(output["venue_class"], "UNKNOWN")

    def test_historical_invalid_trf_code_stays_unknown(self):
        record = self.trade(exchange=4, trf_id=999)
        output = historical("trades", [record])["private_rows"][0]
        self.assertEqual(output["venue_class"], "UNKNOWN")

    def test_historical_recognized_trfs_remain_off_exchange(self):
        for trf_id in (201, 202, 203):
            with self.subTest(trf_id=trf_id):
                rec = self.trade(exchange=4, trf_id=trf_id)
                observed = historical("trades", [rec])["private_rows"][0]
                self.assertEqual(observed["venue_class"], "TRF")

if __name__ == "__main__":
    unittest.main()
