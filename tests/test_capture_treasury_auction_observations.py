"""Collector boundary tests: actual receipt store -> pure lifecycle consumer."""
import hashlib
import itertools
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from urllib.request import Request

from engine import treasury_auction_lifecycle as lifecycle
from scripts import capture_treasury_auction_observations as capture_script


FIXTURE = Path(__file__).parent / "fixtures" / "treasury_auction_lifecycle" / "bill_future_nonstandard_deadline.json"
AT = datetime(2026, 10, 8, 22, tzinfo=timezone.utc)


def clock(base=AT):
    ticks = itertools.count()
    return lambda: base + timedelta(seconds=next(ticks))


def fetcher(body):
    return lambda url: (body, {"final_url": url, "http_status": 200, "http_last_modified": "not a knowledge clock"})


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.body = json.dumps([json.loads(FIXTURE.read_text())]).encode()

    def tearDown(self):
        self.temp.cleanup()

    def run_capture(self, body=None, **kwargs):
        return capture_script.capture(self.root, source_names=["upcoming"],
                                      fetcher=fetcher(body or self.body), clock=clock(), **kwargs)

    def test_availability_after_body_and_parse_not_http_metadata(self):
        result = self.run_capture()
        row = result["captures"][0]
        envelope = json.loads(Path(row["path"]).read_text())
        self.assertEqual(envelope["metadata"]["body_received_at"], (AT + timedelta(seconds=1)).isoformat())
        self.assertEqual(envelope["observed_at"], (AT + timedelta(seconds=2)).isoformat())
        self.assertIsNone(envelope["metadata"]["publication_time"])
        self.assertEqual(envelope["payload_sha256"], hashlib.sha256(self.body).hexdigest())
        self.assertEqual(lifecycle.snapshot(self.root, AT + timedelta(seconds=1))["events"], [])
        visible = lifecycle.snapshot(self.root, AT + timedelta(seconds=3))
        self.assertEqual(visible["coverage"]["known_upcoming_count"], 1)
        self.assertEqual(visible["events"][0]["competitive_deadline_utc"], "2026-10-13T17:00:00+00:00")

    def test_repeat_is_idempotent_and_does_not_overwrite_prior_receipt(self):
        first = self.run_capture()["captures"][0]
        original = Path(first["path"]).read_bytes()
        second = self.run_capture()["captures"][0]
        self.assertEqual(first["path"], second["path"])
        self.assertEqual(Path(first["path"]).read_bytes(), original)
        self.assertEqual(len(list(Path(first["path"]).parent.glob("*.json"))), 1)

    def test_failure_retains_last_success_with_older_source_age(self):
        self.run_capture()
        def broken(url):
            raise TimeoutError("synthetic timeout")
        result = capture_script.capture(self.root, source_names=["upcoming"], fetcher=broken,
                                        clock=clock(AT + timedelta(minutes=5)))
        self.assertEqual(result["captures"][0]["status"], "unavailable")
        context = lifecycle.snapshot(self.root, AT + timedelta(minutes=10))
        self.assertEqual(context["status"], "degraded")
        self.assertEqual(context["coverage"]["known_upcoming_count"], 1)
        self.assertEqual(context["source_observed_at"], (AT + timedelta(seconds=2)).isoformat())
        self.assertTrue(any(s["status"] == "unavailable" for s in context["source_states"]))

    def test_malformed_body_retained_but_not_a_valid_empty_calendar(self):
        result = self.run_capture(body=b"{broken")
        row = result["captures"][0]
        self.assertNotEqual(row["status"], "available")
        self.assertEqual(json.loads(Path(row["path"]).read_text())["raw_text"], "{broken")
        context = lifecycle.snapshot(self.root, AT + timedelta(minutes=1))
        self.assertIsNone(context["coverage"]["known_upcoming_count"])
        self.assertTrue(context["quarantine"])

    def test_untrusted_final_url_and_redirect_rejected(self):
        result = capture_script.capture(self.root, source_names=["upcoming"], clock=clock(),
            fetcher=lambda url: (self.body, {"final_url": "https://untrusted.example/auction-data"}))
        self.assertEqual(result["captures"][0]["status"], "unavailable")
        context = lifecycle.snapshot(self.root, AT + timedelta(minutes=1))
        self.assertEqual(context["events"], [])
        request = Request(capture_script.SOURCES["upcoming"][1])
        with self.assertRaises(ValueError):
            capture_script._OfficialRedirects().redirect_request(request, None, 302, "found", {}, "http://www.treasurydirect.gov/plain")

    def test_non_utf8_body_retained_for_audit_and_not_parsed(self):
        row = self.run_capture(body=b"\xff")["captures"][0]
        envelope = json.loads(Path(row["path"]).read_text())
        self.assertEqual(row["status"], "unavailable")
        self.assertEqual(envelope["unparsed_body_sha256"], hashlib.sha256(b"\xff").hexdigest())
        self.assertNotIn("raw_text", envelope)


if __name__ == "__main__":
    unittest.main()
