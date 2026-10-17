"""Actual feed producer serialization and existing-risk invariance, offline."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import engine
from engine import treasury_auction_lifecycle as lifecycle
from scripts import build_feeds

FIXTURES = Path(__file__).parent / "fixtures" / "treasury_auction_lifecycle"
AT = datetime(2026, 10, 8, 23, tzinfo=timezone.utc)


class FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return AT


class SovereignFeedTests(unittest.TestCase):
    def _build_with_incumbent(self, fail_auction=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data"
            receipt_dir = data / "treasury_auctions" / "observations"
            receipt_dir.mkdir(parents=True)
            raw = json.dumps([json.loads((FIXTURES / "bill_future_nonstandard_deadline.json").read_text())])
            receipt = lifecycle.make_observation(raw, source_kind="treasurydirect_json",
                source_url="https://www.treasurydirect.gov/TA_WS/securities/upcoming?format=json",
                observed_at="2026-10-08T22:00:00Z")
            (receipt_dir / "one.json").write_text(json.dumps(receipt))
            regime_dir = data / "regime"
            regime_dir.mkdir()
            incumbent = {"risk_radar": {"schema_version": "risk_radar.v2", "asof": "2026-10-07", "state": "CAUTION", "sentinel": [2, 7]}}
            regime_path = regime_dir / "latest.json"
            regime_path.write_text(json.dumps(incumbent))
            preimage = regime_path.read_bytes()
            macro = [{"type": "CPI", "date": "2026-10-14", "impact": "high"}]
            calendar = types.ModuleType("engine.event_calendar")
            calendar.us_macro_events = lambda *args: copy.deepcopy(macro)
            calendar.high_impact_strip = lambda *args: copy.deepcopy(macro)
            calendar.commodity_events = lambda *args: []
            international = types.ModuleType("engine.risk_radar_intl")
            international.PROFILES = {}
            international.snapshot = lambda *args: {}
            with patch.object(build_feeds.config, "ROOT", root), \
                 patch.object(build_feeds.config, "load", return_value={"storage": {"site_dir": "site"}}), \
                 patch.object(build_feeds.config, "data_dir", return_value=data), \
                 patch.object(build_feeds, "datetime", FixedClock), \
                 patch.object(engine, "event_calendar", calendar, create=True), \
                 patch.dict("sys.modules", {"engine.event_calendar": calendar, "engine.risk_radar_intl": international}):
                if fail_auction:
                    with patch.object(lifecycle, "snapshot", side_effect=RuntimeError("controlled auction reader failure")):
                        metadata = build_feeds.build()
                else:
                    metadata = build_feeds.build()
            feed = json.loads((root / "site" / "feeds" / "event_calendar.json").read_text())
            context = feed["sovereign_auction_context"]
            self.assertEqual(feed["us_macro"], macro)
            self.assertEqual(feed["high_impact"], macro)
            self.assertEqual(feed["horizon_days"], 21)
            if fail_auction:
                self.assertIsNone(context)
            else:
                self.assertEqual(context["coverage"]["horizon_days"], 30)
                self.assertEqual(context["source_observed_at"], "2026-10-08T22:00:00+00:00")
                self.assertEqual(context["decision_cutoff_utc"], AT.isoformat())
                self.assertEqual(context["events"][0]["competitive_deadline_utc"], "2026-10-13T17:00:00+00:00")
                self.assertIsNone(context["events"][0]["result"])
                self.assertIsNone(context["probabilities"])
            self.assertEqual(regime_path.read_bytes(), preimage)
            radar = json.loads((root / "site" / "feeds" / "risk_radar.json").read_text())
            self.assertEqual(radar, incumbent["risk_radar"])
            def walk(value):
                if isinstance(value, dict):
                    self.assertFalse({"auction_stress", "treasury_auctions", "stressed", "band"} & value.keys())
                    for child in value.values():
                        walk(child)
                elif isinstance(value, list):
                    for child in value:
                        walk(child)
            walk(context)
            self.assertIn("event_calendar.json", metadata)

    def test_source_to_existing_feed_does_not_modify_incumbent_risk(self):
        self._build_with_incumbent()

    def test_auction_reader_failure_retains_incumbent_calendar_and_risk(self):
        self._build_with_incumbent(fail_auction=True)

    def test_missing_results_remain_visible_after_next_midnight(self):
        for missing_deadline in (False, True):
            with self.subTest(missing_deadline=missing_deadline):
                row = json.loads((FIXTURES / "bill_future_nonstandard_deadline.json").read_text())
                if missing_deadline:
                    row["closingTimeCompetitive"] = ""
                receipt = lifecycle.make_observation(json.dumps([row]), source_kind="treasurydirect_json",
                    source_url="https://www.treasurydirect.gov/TA_WS/securities/upcoming?format=json",
                    observed_at="2026-10-08T22:00:00Z")
                context = lifecycle.build_context([receipt], "2026-10-14T12:00:00Z")
                self.assertEqual(context["coverage"]["known_upcoming_count"], 0)
                self.assertEqual(context["coverage"]["awaiting_result_count"], 1)
                self.assertEqual(context["events"][0]["physical_state"], "AWAITING_RESULT")
                self.assertIsNone(context["events"][0]["result"])
                self.assertIsNone(context["events"][0]["settled_payment_observed"])


if __name__ == "__main__":
    unittest.main()
