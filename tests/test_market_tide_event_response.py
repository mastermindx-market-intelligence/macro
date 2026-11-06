"""Synthetic, source-independent checks for Market Tide event-response semantics."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
import unittest

from engine.market_tide_event_response import compose


def source(*, observed="2026-11-04T14:29:00Z",
           usable="2026-11-04T14:29:20Z", status="complete"):
    return {
        "source_ref": "synthetic:minute-bar", "revision": "v1",
        "rights_ref": "synthetic:license", "observed_at": observed,
        "usable_at": usable, "status": status,
    }


def request():
    return {
        "decision_at": "2026-11-04T14:30:00Z",
        "max_age_seconds": 90,
        "events": [
            {
                "event_id": "synthetic:election",
                "event_type": "election",
                "known_at": "2026-11-04T10:00:00Z",
                "resolution_state": "unresolved",
                "source_ref": "synthetic:official", "revision": "r1",
                "rights_ref": "synthetic:license",
            },
            {
                "event_id": "synthetic:earnings",
                "event_type": "earnings",
                "known_at": "2026-11-04T11:00:00Z",
                "resolution_state": "resolved",
                "resolved_at": "2026-11-04T11:00:00Z",
                "resolution_ref": "synthetic:earnings-release",
                "source_ref": "synthetic:filing", "revision": "r1",
                "rights_ref": "synthetic:license",
            },
        ],
        "market": {**source(), "return_pct": 2.0},
        "securities": [
            {
                "security_id": "synthetic:US:MCD", "ticker": "MCD",
                "source": source(), "return_pct": 6.0,
                "sector_return_pct": 3.0,
                "market_beta": 1.0, "sector_excess_beta": 1.0,
                "factor_fit_known_at": "2026-11-03T20:00:00Z",
                "event_start_at": "2026-11-04T03:00:00Z",
                "event_links": [
                    {
                        "event_id": "synthetic:earnings", "channel": "consumer_demand",
                        "source_ref": "synthetic:filing", "known_at": "2026-11-04T11:00:00Z",
                        "evidence_class": "verified_fact", "scenario_direction": None,
                    },
                    {
                        "event_id": "synthetic:election", "channel": "policy_scenario",
                        "source_ref": "synthetic:research", "known_at": "2026-11-04T10:00:00Z",
                        "evidence_class": "hypothesis", "scenario_direction": "mixed",
                    },
                ],
            },
            {
                "security_id": "synthetic:US:SEMI", "ticker": "SEMI",
                "source": source(), "return_pct": -3.0,
                "sector_return_pct": -2.0,
                "market_beta": 1.0, "sector_excess_beta": 1.0,
                "factor_fit_known_at": "2026-11-03T20:00:00Z",
                "event_start_at": "2026-11-04T03:00:00Z",
                "event_links": [],
            },
        ],
    }


class EventResponse(unittest.TestCase):
    def test_descriptive_separate_catalysts_and_residual(self):
        out = compose(request())
        self.assertEqual(out["schema"], "market_tide.event_response/v1")
        self.assertEqual(out["coverage"], {
            "eligible": 2, "observed": 2, "modeled": 2, "unavailable": 0,
            "event_links_withheld": 0,
        })
        mcd = out["securities"][0]
        self.assertEqual(mcd["decomposition"], {
            "market_pct": 2.0, "sector_excess_pct": 1.0,
            "unexplained_pct": 3.0,
            "method": "market_plus_sector_excess/v1",
            "causal_attribution": False,
        })
        self.assertEqual(
            [link["event_id"] for link in mcd["event_links"]],
            ["synthetic:earnings", "synthetic:election"])
        self.assertFalse(any(link["causality_established"] for link in mcd["event_links"]))
        self.assertEqual(out["securities"][1]["decomposition"]["unexplained_pct"], -1.0)

    def test_unannounced_event_is_entirely_withheld(self):
        req = request()
        req["events"][1]["known_at"] = "2026-11-04T14:31:00Z"
        out = compose(req)
        self.assertEqual(out["event_count_withheld"], 1)
        self.assertEqual(out["event_count_known"], 1)
        self.assertEqual(out["coverage"]["event_links_withheld"], 1)
        self.assertNotIn("synthetic:earnings", str(out["events"]))
        self.assertNotIn("synthetic:earnings", str(out["securities"][0]["event_links"]))

    def test_link_not_known_at_decision_is_not_exposed(self):
        req = request()
        req["securities"][0]["event_links"][0]["known_at"] = "2026-11-04T14:31:00Z"
        out = compose(req)
        self.assertEqual(out["coverage"]["event_links_withheld"], 1)
        self.assertEqual(len(out["securities"][0]["event_links"]), 1)

    def test_unverified_resolution_cannot_support_link(self):
        req = request()
        req["events"][1].pop("resolution_ref")
        out = compose(req)
        self.assertEqual(out["events"][1]["resolution_state"], "unverified")
        self.assertEqual(out["coverage"]["event_links_withheld"], 1)

    def test_stale_security_preserves_eligible_denominator(self):
        req = request()
        req["securities"][1]["source"] = source(
            observed="2026-11-04T14:15:00Z",
            usable="2026-11-04T14:15:20Z")
        out = compose(req)
        self.assertEqual(out["coverage"]["eligible"], 2)
        self.assertEqual(out["coverage"]["observed"], 1)
        self.assertEqual(out["coverage"]["modeled"], 1)
        self.assertEqual(out["securities"][1]["status"], "unavailable")
        self.assertEqual(out["securities"][1]["reason"], "STALE_SOURCE")
        self.assertIsNone(out["securities"][1]["return_pct"])

    def test_future_usable_security_does_not_create_return(self):
        req = request()
        req["securities"][0]["source"]["usable_at"] = "2026-11-04T14:31:00Z"
        out = compose(req)
        self.assertEqual(out["securities"][0]["reason"], "SOURCE_NOT_YET_USABLE")
        self.assertIsNone(out["securities"][0]["decomposition"])

    def test_inverted_source_clock_unavailable(self):
        req = request()
        req["securities"][0]["source"]["observed_at"] = "2026-11-04T14:32:00Z"
        out = compose(req)
        self.assertEqual(out["securities"][0]["reason"], "IMPOSSIBLE_SOURCE_CLOCK")

    def test_partial_market_snapshot_does_not_fabricate_residual(self):
        req = request()
        req["market"]["status"] = "unavailable"
        out = compose(req)
        self.assertEqual(out["coverage"]["observed"], 2)
        self.assertEqual(out["coverage"]["modeled"], 0)
        self.assertIsNone(out["securities"][0]["decomposition"])
        self.assertEqual(out["market_reason"], "SOURCE_NOT_ADMITTED")

    def test_factor_fit_after_catalyst_cannot_generate_residual(self):
        req = request()
        req["securities"][0]["factor_fit_known_at"] = "2026-11-04T14:00:00Z"
        out = compose(req)
        self.assertEqual(out["coverage"]["modeled"], 1)
        self.assertIsNone(out["securities"][0]["decomposition"])

    def test_missing_return_is_unavailable_not_zero(self):
        req = request()
        req["securities"][0]["return_pct"] = None
        out = compose(req)
        self.assertIsNone(out["securities"][0]["return_pct"])
        self.assertEqual(out["securities"][0]["reason"], "MISSING_SECURITY_RETURN")

    def test_negative_residual_and_missing_sector_are_distinct(self):
        req = request()
        req["securities"][0]["return_pct"] = -9.0
        req["securities"][1]["sector_return_pct"] = None
        out = compose(req)
        self.assertEqual(out["securities"][0]["decomposition"]["unexplained_pct"], -12.0)
        self.assertIsNone(out["securities"][1]["decomposition"])

    def test_duplicate_security_id_is_rejected(self):
        req = request()
        req["securities"][1]["security_id"] = req["securities"][0]["security_id"]
        with self.assertRaisesRegex(ValueError, "duplicate security_id"):
            compose(req)

    def test_duplicate_event_identity_is_rejected(self):
        req = request()
        req["events"][1]["event_id"] = req["events"][0]["event_id"]
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            compose(req)

    def test_nonfinite_data_is_rejected(self):
        req = request()
        req["securities"][0]["return_pct"] = math.nan
        with self.assertRaisesRegex(ValueError, "finite number"):
            compose(req)

    def test_timezone_and_bound_validation(self):
        req = request()
        req["decision_at"] = "2026-11-04T14:30:00"
        with self.assertRaisesRegex(ValueError, "timezone"):
            compose(req)
        req["decision_at"] = "2026-11-04T14:30:00Z"
        req["max_age_seconds"] = 0
        with self.assertRaisesRegex(ValueError, "max_age_seconds"):
            compose(req)

    def test_bounded_ingress_and_unknown_link_schema(self):
        req = request()
        req["events"] = [req["events"][0]] * 257
        with self.assertRaisesRegex(ValueError, "bounded"):
            compose(req)
        req = request()
        req["securities"][0]["event_links"][0]["evidence_class"] = "trading_decision"
        with self.assertRaisesRegex(ValueError, "evidence class"):
            compose(req)

    def test_deterministic_read_only_and_zero_authority(self):
        req = request()
        before = deepcopy(req)
        out1 = compose(req)
        out2 = compose(req)
        self.assertEqual(out1, out2)
        self.assertEqual(req, before)
        self.assertTrue(all(value is False for value in out1["authority"].values()))
        self.assertIsNone(out1["forecast"])
        self.assertIsNone(out1["hedge_flow"])


if __name__ == "__main__":
    unittest.main()
