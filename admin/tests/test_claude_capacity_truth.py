"""Claude capacity observatory: unknown is not zero, resets are not quota.

These tests require no provider secrets, live subscriptions or network access.
They verify the ingestion boundary, not the provider's actual available balance.
"""
from __future__ import annotations

import hashlib
import time
import unittest

from admin.capacity_fabric_schema import SCHEMA, clean_snapshot
from admin.capacity_fabric_observer import _weekly_reset_expiring


def snapshot(now):
    return {
        "schema": SCHEMA,
        "epoch": hashlib.sha256(b"claude-capacity-truth").hexdigest()[:24],
        "started_at": now - 60,
        "generated_at": now,
        "sequence": 1,
        "routes": [],
        "active": [],
        "recent": [],
        "series": [],
        "aliases": {},
        "totals": {},
        "claude": {
            "reachable": True,
            "observed_at": now,
            "accounts": [{
                "id": "ab12cd34",
                "label": "max-4",
                "used_5h": 0,
                "remaining_5h": 1000,
                "budget_5h": 1000,
                "drain": False,
                "families": {
                    "opus": {
                        "used_weekly": 560,
                        "remaining_weekly": 840,
                        "budget_weekly": 1400,
                        "cooldown_until": now + 1800,
                        "weekly_resets_at": now + 3 * 86400,
                        "weekly_reset_source": "provider",
                    }
                },
            }]
        },
    }


class ClaudeCapacityTruth(unittest.TestCase):
    def test_explicit_zero_is_preserved_even_if_lane_is_benched(self):
        now = time.time()
        result = clean_snapshot(snapshot(now))
        account = result["claude"]["accounts"][0]
        lane = account["families"]["opus"]
        self.assertEqual(account["used_5h"], 0)
        self.assertEqual(lane["used_weekly"], 560)
        self.assertEqual(lane["remaining_weekly"], 840)
        self.assertGreater(lane["cooldown_until"], now)

    def test_missing_usage_remains_unknown_not_zero(self):
        now = time.time()
        sample = snapshot(now)
        account = sample["claude"]["accounts"][0]
        account.pop("used_5h")
        account["families"]["opus"].pop("used_weekly")
        result = clean_snapshot(sample)
        cleaned = result["claude"]["accounts"][0]
        self.assertIsNone(cleaned["used_5h"])
        self.assertIsNone(cleaned["families"]["opus"]["used_weekly"])
        self.assertEqual(cleaned["families"]["opus"]["remaining_weekly"], 840)

    def test_mismatched_gateway_counters_are_not_silently_reconciled(self):
        sample = snapshot(time.time())
        sample["claude"]["accounts"][0]["families"]["opus"]["remaining_weekly"] = 1399
        result = clean_snapshot(sample)
        lane = result["claude"]["accounts"][0]["families"]["opus"]
        self.assertEqual((lane["used_weekly"], lane["remaining_weekly"], lane["budget_weekly"]),
                         (560, 1399, 1400))

    def test_missing_five_hour_used_and_remaining_both_stay_unknown(self):
        sample = snapshot(time.time())
        sample["claude"]["accounts"][0]["used_5h"] = None
        sample["claude"]["accounts"][0]["remaining_5h"] = None
        account = clean_snapshot(sample)["claude"]["accounts"][0]
        self.assertIsNone(account["used_5h"])
        self.assertIsNone(account["remaining_5h"])

    def test_expiring_reset_only_when_within_future_horizon(self):
        now = 2_000_000_000
        self.assertTrue(_weekly_reset_expiring(now + 1800, 3600, now))
        self.assertTrue(_weekly_reset_expiring(now + 3600, 3600, now))
        self.assertFalse(_weekly_reset_expiring(now - 1, 3600, now))
        self.assertFalse(_weekly_reset_expiring(now + 3601, 3600, now))
        self.assertFalse(_weekly_reset_expiring(None, 3600, now))
        self.assertFalse(_weekly_reset_expiring("bad_timestamp", 3600, now))
        self.assertFalse(_weekly_reset_expiring(now + 5, "bad_horizon", now))
        self.assertFalse(_weekly_reset_expiring(now + 5, -1, now))

    def test_provider_reset_provenance_does_not_prove_quota_consumption(self):
        sample = snapshot(time.time())
        lane = sample["claude"]["accounts"][0]["families"]["opus"]
        lane.pop("used_weekly")
        lane["weekly_reset_source"] = "provider"
        sanitized = clean_snapshot(sample)["claude"]["accounts"][0]["families"]["opus"]
        self.assertEqual(sanitized["weekly_reset_source"], "provider")
        self.assertIsNone(sanitized["used_weekly"])


if __name__ == "__main__":
    unittest.main()
