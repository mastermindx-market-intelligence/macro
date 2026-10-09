"""Observed v7 XML and adversarial source clocks; no synthetic release history."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from engine import treasury_auction_lifecycle as lifecycle
from scripts import capture_treasury_auction_observations as capture_script

AUDIT = Path(__file__).parents[1] / "research/sovereign_auction_pressure/source_audit"
AT = "2026-10-08T23:00:00Z"


def notice(name, raw=None, observed="2026-10-08T22:12:22.414829Z"):
    source = next(r for r in json.loads((AUDIT / "SOURCE_RECEIPTS.json").read_text())
                  if r["source"] == "xml_" + name)
    body = (AUDIT / "raw" / ("xml_" + name + ".xml")).read_bytes()
    assert hashlib.sha256(body).hexdigest() == source["sha256"]
    return lifecycle.make_observation(raw if raw is not None else body,
        source_kind="treasury_auction_notice_xml", source_url=source["url"],
        observed_at=observed, metadata={"request_started_at": source["request_started_at"],
            "verified_present_at": source["verified_present_at"],
            "observed_at_basis": "retained_verified_availability_upper_bound"})


class OfficialNoticeTests(unittest.TestCase):
    def event(self, name, **kwargs):
        out = lifecycle.build_context([notice(name, **kwargs)], AT, horizon_days=366)
        self.assertEqual(out["status"], "available", out["source_states"])
        return out["events"][0]

    def test_real_announcement_units_and_source_clocks(self):
        e = self.event("A_20261008_1")
        self.assertEqual(e["offering_amount_usd"], "95000000000")
        self.assertEqual(e["source_state"], "ANNOUNCED")
        self.assertEqual(e["competitive_deadline_utc"], "2026-10-13T17:00:00+00:00")
        self.assertEqual(e["noncompetitive_deadline_utc"], "2026-10-13T16:00:00+00:00")
        self.assertEqual(e["maturity_date"], "2026-11-27")
        self.assertIsNone(e["publication_time"])
        self.assertIsNone(e["body_received_at"])
        self.assertEqual(e["known_at"], "2026-10-08T22:12:22.414829+00:00")

    def test_real_results_dollars_and_rate_axes(self):
        for name, kind, amount in [("R_20261001_1", "Bill", "100000000000"),
                ("R_20261007_2", "Note", "39000000000"),
                ("R_20261008_3", "Bond", "22000000000"),
                ("R_20260917_3", "TIPS", "19000000000"),
                ("R_20260923_2", "FRN", "28000000000")]:
            with self.subTest(name=name):
                e = self.event(name)
                self.assertEqual(e["normalized_class"], kind)
                self.assertEqual(e["offering_amount_usd"], amount)
                self.assertEqual(e["source_state"], "RESULT_OBSERVED")
                self.assertIsNone(e["publication_time"])
                self.assertIsNotNone(e["result_release_time_raw"])
                self.assertLess(int(e["result"]["competitive_accepted_usd"]), 10**12)
                self.assertIsNone(e["settled_payment_observed"])
                self.assertIsNone(e["probabilities"])
        e = self.event("R_20260923_2")
        self.assertEqual(e["result"]["high_discount_margin_pct"], "0.040")
        self.assertIsNone(e["result"]["nominal_yield_pct"])

    def test_cmb_legal_xml_does_not_invent_missing_cmb_flag(self):
        e = self.event("R_20260521_3")
        self.assertEqual(e["security_term"], "27-Day")
        self.assertIn("cmb_status_not_encoded_in_v7_xml", e["null_reasons"])
        self.assertIsNone(e["raw_class_flags"]["cashManagementBillCMB"])
        # Existing explicitly class-qualified JSON remains the CMB authority.
        raw = (Path(__file__).parent / "fixtures/treasury_auction_lifecycle/cash_management_bill.json").read_text()
        api = lifecycle.make_observation("[" + raw + "]", source_kind="treasurydirect_json",
            source_url="https://www.treasurydirect.gov/TA_WS/securities/search", observed_at=AT)
        out = lifecycle.build_context([notice("R_20260521_3"), api], AT, 366)
        self.assertEqual(out["episodes"][0]["normalized_class"], "CMB")

    def test_xml_unknown_schema_duplicate_sections_or_entities_are_visible(self):
        body = notice("A_20261008_1")["raw_text"]
        bad = [body.replace("Auction_v7_0_0.xsd", "Auction_v8_0_0.xsd"),
            body.replace("</td:AuctionData>", "<AuctionResults/><AuctionResults/></td:AuctionData>"),
            body.replace("<CUSIP>", "<CUSIP><nested>", 1),
            body.replace("<AuctionAnnouncement>", "<AuctionAnnouncement><OperationStatus>Cancelled</OperationStatus>")]
        for raw in bad:
            with self.subTest(raw=raw[:100]):
                out = lifecycle.build_context([notice("A_20261008_1", raw=raw)], AT)
                self.assertFalse(out["events"])
                self.assertNotEqual(out["status"], "available")
                self.assertIsNone(out["coverage"]["known_upcoming_count"])

    def test_synthetic_late_amendment_retains_prior_deadline(self):
        a = notice("A_20261008_1")
        # Synthetic mutation of real bytes, never a claimed historical amendment.
        b = notice("A_20261008_1", raw=a["raw_text"].replace("<CompetitiveClosingTime>13:00", "<CompetitiveClosingTime>11:30"),
            observed="2026-10-08T23:30:00Z")
        out = lifecycle.build_context([b, a], AT)
        self.assertEqual(out["events"][0]["competitive_deadline_utc"], "2026-10-13T17:00:00+00:00")
        later = lifecycle.build_context([a, b], "2026-10-09T00:00:00Z")
        self.assertEqual(later["events"][0]["competitive_deadline_utc"], "2026-10-13T15:30:00+00:00")
        self.assertEqual(len(later["events"][0]["observation_versions"]), 2)

    def test_future_result_and_ambiguous_xml_identity_withheld(self):
        a = notice("R_20261008_3")
        a["observed_at"] = "2026-10-08T16:00:00+00:00"
        a["metadata"] = {}  # synthetic receipt clock for this negative test
        out = lifecycle.build_context([a], AT)
        self.assertFalse(out["events"])
        self.assertEqual(out["quarantine"][0]["reason"], "future_result_bearing_contradiction")

    def test_notice_capture_is_bounded_and_uses_actual_receipt_clock(self):
        import tempfile
        ticks = iter([datetime(2026, 10, 9, 1, tzinfo=timezone.utc) + timedelta(seconds=i) for i in range(3)])
        body = notice("A_20261008_1")["raw_text"].encode()
        urls = []
        def fetch(url):
            urls.append(url)
            return body, {"final_url": url, "http_status": 200}
        with tempfile.TemporaryDirectory() as root:
            out = capture_script.capture(root, source_names=[], notice_names=["A_20261008_1.xml"],
                fetcher=fetch, clock=lambda: next(ticks))
            self.assertEqual(urls, ["https://www.treasurydirect.gov/xml/A_20261008_1.xml"])
            receipt = json.loads(Path(out["captures"][0]["path"]).read_text())
            self.assertEqual(receipt["observed_at"], "2026-10-09T01:00:02+00:00")
            self.assertEqual(receipt["metadata"]["body_received_at"], "2026-10-09T01:00:01+00:00")
            self.assertEqual(receipt["payload_sha256"], hashlib.sha256(body).hexdigest())
        for name in ["../A_20261008_1.xml", "https://evil.example/a.xml", "A_20260230_1.xml"]:
            with self.assertRaises(ValueError):
                capture_script.capture("unused", source_names=[], notice_names=[name], fetcher=fetch)


if __name__ == "__main__":
    unittest.main()
