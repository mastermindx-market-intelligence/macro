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

if __name__ == "__main__":
    unittest.main()
