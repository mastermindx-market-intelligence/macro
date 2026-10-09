"""Cutoff selection must survive copied files and receipt count boundaries."""
import json
import os
from pathlib import Path
import random
import tempfile
import unittest

from engine import treasury_auction_lifecycle as lifecycle
from tests.test_treasury_auction_lifecycle import receipt, row, NOW


class AuctionArchiveTests(unittest.TestCase):
    def test_direct_envelopes_exclude_future_before_the_projection_bound(self):
        old = receipt(observed="2026-10-08T20:00:00Z")
        future = [receipt(observed="2026-10-09T20:00:00Z") for _ in range(160)]
        a = lifecycle.build_context(future + [old], NOW)
        b = lifecycle.build_context([old] + future, NOW)
        self.assertEqual(a["events"], b["events"])
        self.assertEqual(a["events"], lifecycle.build_context([old], NOW)["events"])
        self.assertFalse(a["coverage"]["truncated"])

    def test_malformed_origin_cannot_crash_archive_health(self):
        invalid = receipt(); invalid["source_kind"] = ["hostile"]
        with tempfile.TemporaryDirectory() as root:
            d = Path(root) / "treasury_auctions/observations"; d.mkdir(parents=True)
            for i in range(lifecycle.MAX_FILES + 1):
                (d / f"bad-{i}.json").write_text(json.dumps(invalid))
            out = lifecycle.snapshot(Path(root), NOW)
        self.assertFalse(out["events"])
        self.assertTrue(out["quarantine"])
        self.assertTrue(out["coverage"]["truncated"])

    def test_over_scan_bound_direct_stream_fails_closed(self):
        values = [receipt()] * (lifecycle.MAX_ARCHIVE_FILES + 1)
        out = lifecycle.build_context(values, NOW)
        self.assertFalse(out["events"])
        self.assertTrue(out["coverage"]["truncated"])
        self.assertTrue(any(q["reason"] == "direct_receipt_scan_limit" for q in out["quarantine"]))

    def test_equal_clock_cohort_at_bound_never_chooses_an_arbitrary_revision(self):
        values = []
        for i in range(lifecycle.MAX_ENVELOPES + 1):
            r = row(); r["offeringAmount"] = str(i)
            values.append(receipt([r]))
        for envelopes in (values, list(reversed(values))):
            out = lifecycle.build_context(envelopes, NOW)
            self.assertFalse(out["events"])
            self.assertTrue(out["coverage"]["truncated"])
            self.assertIsNone(out["coverage"]["known_upcoming_count"])

    def test_long_outage_pins_last_good_without_complete_count_claim(self):
        with tempfile.TemporaryDirectory() as root:
            d = Path(root) / "treasury_auctions/observations"; d.mkdir(parents=True)
            good = receipt(observed="2026-10-08T20:00:00Z")
            (d / "good.json").write_text(json.dumps(good))
            for i in range(150):
                failure = dict(good, status="unavailable", error="TLS failure",
                    observed_at=f"2026-10-08T21:{i // 60:02d}:{i % 60:02d}Z")
                (d / f"fail-{i:03}.json").write_text(json.dumps(failure))
            out = lifecycle.snapshot(Path(root), NOW)
            self.assertEqual(len(out["events"]), 1)
            self.assertEqual(out["source_health"][0]["last_valid_observation_at"], "2026-10-08T20:00:00+00:00")
            self.assertEqual(out["source_health"][0]["latest_attempt_status"], "unavailable")
            self.assertTrue(out["coverage"]["truncated"])
            self.assertIsNone(out["coverage"]["known_upcoming_count"])

    def test_post_cutoff_files_never_evict_prior_known_observation(self):
        with tempfile.TemporaryDirectory() as root:
            d = Path(root) / "treasury_auctions/observations"; d.mkdir(parents=True)
            (d / "old.json").write_text(json.dumps(receipt(observed="2026-10-08T20:00:00Z")))
            for i in range(lifecycle.MAX_FILES + 20):
                (d / f"future-{i:03}.json").write_text(json.dumps(receipt(observed="2026-10-09T20:00:00Z")))
            before = lifecycle.snapshot(Path(root), NOW)
            self.assertEqual(len(before["events"]), 1)
            self.assertFalse(before["coverage"]["truncated"])
            self.assertEqual(before["coverage"]["known_upcoming_count"], 1)
            # mtime changes and directory enumeration cannot change financial facts.
            for f in d.glob("*.json"):
                os.utime(f, (random.Random(f.name).random() * 1000000,) * 2)
            after = lifecycle.snapshot(Path(root), NOW)
            self.assertEqual(before, after)
            for f in d.glob("future-*.json"): f.unlink()
            withheld = lifecycle.snapshot(Path(root), NOW)
            self.assertEqual(before["events"], withheld["events"])
            self.assertEqual(before["source_health"], withheld["source_health"])

    def test_stale_source_and_late_failure_do_not_freshen_last_good(self):
        good = receipt(observed="2026-10-06T20:00:00Z")
        failure = dict(good, status="unavailable", error="TLS failure", observed_at="2026-10-08T22:00:00Z")
        out = lifecycle.build_context([failure, good], NOW)
        health = out["source_health"][0]
        self.assertEqual(health["freshness_status"], "STALE")
        self.assertIsNone(health["stale_after_seconds"])
        self.assertEqual(health["context_age_budget_seconds"], 86400)
        self.assertEqual(health["last_valid_observation_at"], "2026-10-06T20:00:00+00:00")
        self.assertEqual(out["status"], "degraded")
        self.assertEqual(len(out["events"]), 1)

    def test_clock_chain_inconsistency_cannot_backdate_availability(self):
        for field in ["request_started_at", "parse_completed_at", "verified_present_at"]:
            env = receipt(observed="2026-10-08T20:00:00Z")
            env["metadata"][field] = "2026-10-08T21:00:00Z"
            out = lifecycle.build_context([env], NOW)
            self.assertEqual(out["events"], [])
            self.assertTrue(out["quarantine"])


if __name__ == "__main__":
    unittest.main()
