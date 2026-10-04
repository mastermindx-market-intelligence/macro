"""TDD coverage for the Market Tide C1 supplied-source preparation bridge.

All inputs are synthetic.  The bridge may transform qualified-looking supplied
evidence, but it may never grant source qualification or forecast/trading
authority.
"""
from __future__ import annotations

import copy
import importlib
import math
import unittest
from datetime import date, datetime, timedelta, timezone

try:
    prep = importlib.import_module("research.options_estate.market_tide_c1_prepare")
except ModuleNotFoundError as exc:
    if exc.name != "research.options_estate.market_tide_c1_prepare":
        raise
    prep = None


def _sessions(n=75):
    out = []
    d = date(2020, 1, 2)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def source_bundle():
    days = _sessions()
    closes = {d: datetime(d.year, d.month, d.day, 20, tzinfo=timezone.utc) for d in days}
    origin_i = 63
    origin = days[origin_i]
    decision = closes[origin] + timedelta(minutes=15)

    sadj = [100.0 * math.exp(0.0010 * i) for i in range(64)]
    tradj = [80.0 * math.exp(0.0015 * i) for i in range(64)]

    feature_prices = []
    for j, d in enumerate(days[:64]):
        feature_prices.append({
            "session": d.isoformat(),
            "close_sadj": sadj[j],
            "close_tradj": tradj[j],
            "available_at": (closes[d] + timedelta(minutes=5)).isoformat(),
        })

    # Outcome series deliberately uses a separate later total-return vintage.
    # The origin is rescaled relative to the feature-vintage TR series.
    label_moves = [0.0, -0.01, -0.02, 0.005, -0.004, 0.01]
    label_origin = 160.0
    label_prices = []
    for j, d in enumerate(days[origin_i: origin_i + 6]):
        label_prices.append({
            "session": d.isoformat(),
            "close_tradj": label_origin * math.exp(label_moves[j]),
            "available_at": (closes[d] + timedelta(minutes=5)).isoformat(),
        })

    return {
        "study": "C1-M1",
        "instrument": "SPY",
        "evidence_kind": "retrospective_supplied",
        "calendar_ref": "synthetic:calendar:v1",
        "coverage_start": days[0].isoformat(),
        "coverage_end": days[-1].isoformat(),
        "calendar": [{"session": d.isoformat(), "close_at": closes[d].isoformat()} for d in days],
        "origins": [{
            "session": origin.isoformat(),
            "decision_at": decision.isoformat(),
            "price_bundle_ref": "synthetic:dual-basis:bundle-v1",
            "price_rights_ref": "synthetic:price-rights:v1",
            "feature_price_identity": {"session": "regular", "venue_scope": "consolidated"},
            "label_price_identity": {"session": "regular", "venue_scope": "consolidated"},
            "feature_sadj_ref": "synthetic:sadj:feature-v1",
            "feature_tradj_ref": "synthetic:tradj:feature-v1",
            "feature_adjustment_asof": (closes[origin] + timedelta(minutes=6)).isoformat(),
            "feature_prices": feature_prices,
            "label_tradj_ref": "synthetic:tradj:label-v2",
            "label_adjustment_asof": (closes[days[origin_i + 5]] + timedelta(minutes=6)).isoformat(),
            "label_prices": label_prices,
            "event_evidence": {
                "known_at": (decision - timedelta(days=2)).isoformat(),
                "coverage_ref": "synthetic:event-window:v1",
                "rights_ref": "synthetic:event-rights:v1",
                "coverage_status": "complete_for_window",
                "features": {"CPI": 1, "NFP": 0, "FOMC": 0},
                "event_times": {
                    "CPI": [(closes[days[origin_i + 1]] - timedelta(hours=6)).isoformat()],
                    "NFP": [],
                    "FOMC": [],
                },
                "negative_coverage_refs": {
                    "NFP": "synthetic:negative:nfp:v1",
                    "FOMC": "synthetic:negative:fomc:v1",
                },
            },
        }],
    }


class PrepareC1(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(prep, "C1 supplied-source preparation bridge is absent")
        self.bundle = source_bundle()

    def test_prepares_exact_dual_basis_measurements(self):
        packet = prep.prepare_packet(self.bundle)
        self.assertEqual(packet["primary_cohort_admitted"], False)
        self.assertEqual(packet["source_qualification"], "not_assessed_by_preparation_bridge")
        self.assertEqual(len(packet["rows"]), 1)
        row = packet["rows"][0]
        self.assertAlmostEqual(row["v20"], .0015, places=12)
        self.assertAlmostEqual(row["trend63"], .063, places=12)
        self.assertAlmostEqual(row["momentum5"], .005, places=12)
        self.assertAlmostEqual(row["y5"], .02 / (.0015 * math.sqrt(5)), places=12)
        self.assertEqual(row["event_flags"], {"CPI": 1, "NFP": 0, "FOMC": 0})
        self.assertEqual(row["label_end_session"], self.bundle["calendar"][68]["session"])
        self.assertEqual(row["price_ref"], "synthetic:dual-basis:bundle-v1")
        self.assertEqual(row["event_ref"], "synthetic:event-window:v1")

    def test_separate_label_vintage_does_not_change_predecision_volatility(self):
        packet = prep.prepare_packet(self.bundle)
        row = packet["rows"][0]
        self.assertAlmostEqual(row["v20"], .0015, places=12)
        # If the feature-vintage origin were incorrectly mixed with label-vintage
        # endpoints, the result would be dominated by the 2x level difference.
        self.assertLess(row["y5"], 20)

    def test_feature_adjustment_vintage_cannot_be_future_known(self):
        b = copy.deepcopy(self.bundle)
        origin = b["origins"][0]
        origin["feature_adjustment_asof"] = (
            datetime.fromisoformat(origin["decision_at"]) + timedelta(seconds=1)
        ).isoformat()
        with self.assertRaisesRegex(ValueError, "feature_adjustment_not_known_at_decision"):
            prep.prepare_packet(b)

    def test_feature_price_cannot_be_available_after_decision(self):
        b = copy.deepcopy(self.bundle)
        origin = b["origins"][0]
        origin["feature_prices"][-1]["available_at"] = (
            datetime.fromisoformat(origin["decision_at"]) + timedelta(seconds=1)
        ).isoformat()
        with self.assertRaisesRegex(ValueError, "feature_price_not_known_at_decision"):
            prep.prepare_packet(b)

    def test_feature_price_cannot_claim_availability_before_its_close(self):
        b = copy.deepcopy(self.bundle)
        origin = b["origins"][0]
        close = datetime.fromisoformat(b["calendar"][63]["close_at"])
        origin["feature_prices"][-1]["available_at"] = (close - timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError, "price_available_before_close"):
            prep.prepare_packet(b)

    def test_ambiguous_price_columns_are_rejected(self):
        b = copy.deepcopy(self.bundle)
        b["origins"][0]["feature_prices"][0]["close"] = 100.0
        with self.assertRaisesRegex(ValueError, "ambiguous_price_column"):
            prep.prepare_packet(b)

    def test_feature_and_label_sessions_must_match_exact_calendar_windows(self):
        b = copy.deepcopy(self.bundle)
        b["origins"][0]["feature_prices"][0]["session"] = b["calendar"][1]["session"]
        with self.assertRaisesRegex(ValueError, "feature_window_session_mismatch"):
            prep.prepare_packet(b)
        b = copy.deepcopy(self.bundle)
        b["origins"][0]["label_prices"][-1]["session"] = b["calendar"][69]["session"]
        with self.assertRaisesRegex(ValueError, "label_window_session_mismatch"):
            prep.prepare_packet(b)

    def test_label_adjustment_vintage_cannot_precede_fifth_close(self):
        b = copy.deepcopy(self.bundle)
        end_close = datetime.fromisoformat(b["calendar"][68]["close_at"])
        b["origins"][0]["label_adjustment_asof"] = (end_close - timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError, "label_adjustment_precedes_outcome"):
            prep.prepare_packet(b)

    def test_zero_event_flag_requires_known_negative_coverage(self):
        b = copy.deepcopy(self.bundle)
        del b["origins"][0]["event_evidence"]["negative_coverage_refs"]["NFP"]
        with self.assertRaisesRegex(ValueError, "negative_event_coverage_unavailable"):
            prep.prepare_packet(b)

    def test_unknown_event_feature_is_not_coerced_to_zero(self):
        b = copy.deepcopy(self.bundle)
        b["origins"][0]["event_evidence"]["features"]["FOMC"] = None
        with self.assertRaisesRegex(ValueError, "event_coverage_unavailable"):
            prep.prepare_packet(b)

    def test_event_time_must_fall_after_decision_and_by_next_close(self):
        b = copy.deepcopy(self.bundle)
        b["origins"][0]["event_evidence"]["event_times"]["CPI"] = [
            b["origins"][0]["decision_at"]
        ]
        with self.assertRaisesRegex(ValueError, "event_time_mismatch"):
            prep.prepare_packet(b)
        b = copy.deepcopy(self.bundle)
        next_close = datetime.fromisoformat(b["calendar"][64]["close_at"])
        b["origins"][0]["event_evidence"]["event_times"]["CPI"] = [
            (next_close + timedelta(seconds=1)).isoformat()
        ]
        with self.assertRaisesRegex(ValueError, "event_time_mismatch"):
            prep.prepare_packet(b)

    def test_event_evidence_must_be_known_by_decision_and_complete_for_window(self):
        b = copy.deepcopy(self.bundle)
        origin = b["origins"][0]
        origin["event_evidence"]["known_at"] = (
            datetime.fromisoformat(origin["decision_at"]) + timedelta(seconds=1)
        ).isoformat()
        with self.assertRaisesRegex(ValueError, "event_evidence_not_known_at_decision"):
            prep.prepare_packet(b)
        b = copy.deepcopy(self.bundle)
        b["origins"][0]["event_evidence"]["coverage_status"] = "partial"
        with self.assertRaisesRegex(ValueError, "event_coverage_unavailable"):
            prep.prepare_packet(b)

    def test_price_session_and_venue_identity_are_required_and_carried(self):
        packet = prep.prepare_packet(self.bundle)
        evidence = packet["rows"][0]["source_evidence"]
        self.assertEqual(evidence["feature_price_identity"], {"session": "regular", "venue_scope": "consolidated"})
        self.assertEqual(evidence["label_price_identity"], {"session": "regular", "venue_scope": "consolidated"})

        b = copy.deepcopy(self.bundle)
        del b["origins"][0]["feature_price_identity"]
        with self.assertRaisesRegex(ValueError, "price_identity_unavailable"):
            prep.prepare_packet(b)

        b = copy.deepcopy(self.bundle)
        b["origins"][0]["label_price_identity"]["session"] = "post"
        with self.assertRaisesRegex(ValueError, "unsupported_price_session_scope"):
            prep.prepare_packet(b)

        b = copy.deepcopy(self.bundle)
        b["origins"][0]["feature_price_identity"]["venue_scope"] = "unknown"
        with self.assertRaisesRegex(ValueError, "price_venue_scope_unavailable"):
            prep.prepare_packet(b)

    def test_price_and_event_rights_references_are_required_and_carried(self):
        packet = prep.prepare_packet(self.bundle)
        evidence = packet["rows"][0]["source_evidence"]
        self.assertEqual(evidence["price_rights_ref"], "synthetic:price-rights:v1")
        self.assertEqual(evidence["event_rights_ref"], "synthetic:event-rights:v1")

        b = copy.deepcopy(self.bundle)
        del b["origins"][0]["price_rights_ref"]
        with self.assertRaisesRegex(ValueError, "price_rights_unavailable"):
            prep.prepare_packet(b)

        b = copy.deepcopy(self.bundle)
        del b["origins"][0]["event_evidence"]["rights_ref"]
        with self.assertRaisesRegex(ValueError, "event_rights_unavailable"):
            prep.prepare_packet(b)

    def test_output_remains_nonadmitted_even_when_inputs_have_owner_refs(self):
        packet = prep.prepare_packet(self.bundle)
        self.assertFalse(packet["primary_cohort_admitted"])
        self.assertFalse(packet["can_publish_forecast"])
        self.assertFalse(packet["may_trade"])
        self.assertIn("source owners must independently qualify", " ".join(packet["limitations"]))


if __name__ == "__main__":
    unittest.main()
