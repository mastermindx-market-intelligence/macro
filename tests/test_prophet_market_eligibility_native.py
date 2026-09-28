"""Real native composer -> GD-6A -> bound view. All observations are synthetic.

Imports the complete existing engine.risk_envelope with no mocked dependencies.
This is function-chain compatibility, not collector/publication/market evidence.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.risk_envelope import SourceRead, compose_envelope, canonical_json
from engine.prophet_market_eligibility import compose_market_eligibility, bind_shadow_view

SESSION = "2026-09-25"
DECISION = "2026-09-28T13:20:00Z"
EXPIRY = "2026-09-28T14:00:00Z"


def sources():
    return [
        SourceRead(source_id="market-state-latest", role="measured_state",
                   state="RISK_ON", score=77, as_of=SESSION, required=True),
        SourceRead(source_id="leadership-crack-latest", role="hazard_evidence",
                   state="BROKEN", hazard_stage="FRAGILE", as_of=SESSION, required=True),
    ]


def board():
    return {
        "board_definition": "us_prophet_v3", "as_of": SESSION,
        "staleness": {"price_through": SESSION, "delayed": False,
                      "unknown": False, "basis": "panel_majority"},
        "buy": [{"ticker": "SYNTH_NATIVE", "prophet": {"rank": 1, "score": 99},
                 "entry_signal": {"status": "buy_now"}, "fictional": True}],
    }


class NativeComposerCompatibility(unittest.TestCase):
    def compose(self, reads=None, **kwargs):
        arguments = dict(sources=sources() if reads is None else reads, market="US",
                         source_session=SESSION, observed_at="2026-09-25T21:00:00Z",
                         produced_at="2026-09-25T21:00:00Z", stale_after=None,
                         revision="settled")
        arguments.update(kwargs)
        native = compose_envelope(**arguments)
        raw_board = json.dumps(board(), ensure_ascii=False).encode("utf-8")
        raw_envelope = (canonical_json(native) + "\n").encode("utf-8")
        binding = dict(expected_board_sha256=sha256(raw_board).hexdigest(),
                       expected_board_definition="us_prophet_v3",
                       expected_source_session=SESSION,
                       expected_envelope_sha256=sha256(raw_envelope).hexdigest(),
                       decision_at=DECISION, valid_until=EXPIRY)
        sidecar = compose_market_eligibility(raw_board, raw_envelope, **binding)
        view_args = dict(binding)
        view_args["expected_decision_at"] = view_args.pop("decision_at")
        view_args["expected_valid_until"] = view_args.pop("valid_until")
        view = bind_shadow_view(sidecar, raw_board, raw_envelope,
                                read_at=DECISION, **view_args)
        self.assertEqual(view["rows"][0]["candidate"], board()["buy"][0])
        self.assertEqual(view["production_behavior"], "UNCHANGED")
        self.assertTrue(all(value is False for value in view["authority"].values()))
        return native, sidecar, view

    def test_real_composer_zero_policy_chain(self):
        native, sidecar, _ = self.compose()
        self.assertEqual(native["policies"], [])
        self.assertEqual(native["policy_summary"]["basis"], "zero_active_policies")
        self.assertEqual(sidecar["source_state"], "AVAILABLE")
        self.assertEqual(sidecar["rows"][0]["market_eligibility"]["action_meaning"],
                         "NO_MARKET_POLICY_CONSTRAINT_NOT_BUY_PERMISSION")

    def test_contradiction_is_not_averaged_into_policy(self):
        native, sidecar, _ = self.compose()
        self.assertEqual(native["measured_state"]["score"], 77)
        self.assertEqual(native["coherence"]["state"], "CONTRADICTORY")
        self.assertEqual(native["hazard_summary"]["stage"], "FRAGILE")
        self.assertEqual(sidecar["source_state"], "AVAILABLE")
        self.assertEqual(sidecar["rows"][0]["market_eligibility"]["constraints"], [])

    def test_required_missing_source(self):
        reads = sources(); reads[1] = replace(reads[1], present=False)
        native, sidecar, _ = self.compose(reads)
        self.assertEqual(native["data_state"], "UNKNOWN")
        self.assertIsNone(native["hazard_summary"]["stage"])
        self.assertEqual(sidecar["source_state"], "UNAVAILABLE")

    def test_required_stale_source(self):
        reads = sources(); reads[1] = replace(reads[1], stale=True)
        native, sidecar, _ = self.compose(reads)
        self.assertEqual(native["data_state"], "DEGRADED")
        self.assertEqual(sidecar["source_state"], "UNAVAILABLE")

    def test_optional_missing_source_stays_explicitly_partial(self):
        reads = sources() + [SourceRead(source_id="optional", role="context", present=False)]
        native, sidecar, _ = self.compose(reads)
        self.assertEqual(native["data_state"], "PARTIAL")
        self.assertEqual(sidecar["source_state"], "UNAVAILABLE")
        # Shadow unavailability still cannot alter the live board or recommendation.
        self.assertEqual(sidecar["production_behavior"], "UNCHANGED")

    def test_native_unknown_clock_not_hidden_by_all_on_session(self):
        reads = sources(); reads[1] = replace(reads[1], as_of=None)
        native, sidecar, _ = self.compose(reads)
        self.assertTrue(native["freshness"]["all_on_session"])
        self.assertEqual(native["data_state"], "FRESH")
        self.assertEqual(sidecar["source_state"], "UNAVAILABLE")
        self.assertIn("ENVELOPE_SOURCE_CLOCKS_UNQUALIFIED", sidecar["errors"])

    def test_optional_native_unknown_clock_is_not_qualified(self):
        reads = sources() + [SourceRead(source_id="optional-radar", role="hazard_evidence",
                                       state="caution", hazard_stage="FRAGILE", as_of=None)]
        native, sidecar, _ = self.compose(reads)
        self.assertEqual(native["data_state"], "FRESH")
        self.assertTrue(native["freshness"]["all_on_session"])
        self.assertIn("optional-radar", native["hazard_summary"]["contributing_sources"])
        self.assertEqual(sidecar["source_state"], "UNAVAILABLE")
        self.assertIn("ENVELOPE_SOURCE_CLOCKS_UNQUALIFIED", sidecar["errors"])

    def test_optional_native_qualified_clock_remains_usable(self):
        reads = sources() + [SourceRead(source_id="optional-radar", role="hazard_evidence",
                                       state="caution", hazard_stage="FRAGILE", as_of=SESSION)]
        _, sidecar, _ = self.compose(reads)
        self.assertEqual(sidecar["source_state"], "AVAILABLE")

    def test_off_session_native_source_rejected(self):
        reads = sources(); reads[1] = replace(reads[1], as_of="2026-09-24")
        _, sidecar, _ = self.compose(reads)
        self.assertIn("ENVELOPE_SOURCE_SESSION_UNQUALIFIED", sidecar["errors"])

    def test_live_provisional_cannot_be_settled_intake(self):
        _, sidecar, _ = self.compose(revision="live_provisional")
        self.assertIn("UNSETTLED_ENVELOPE", sidecar["errors"])

    def test_native_source_order_invariance(self):
        left = self.compose()[1]
        right = self.compose(list(reversed(sources())))[1]
        self.assertEqual(left, right)

    def test_rebake_same_bundle_binds_different_complete_bytes(self):
        native_a, sidecar_a, _ = self.compose()
        native_b, sidecar_b, _ = self.compose(produced_at="2026-09-25T21:01:00Z")
        self.assertEqual(native_a["bundle_id"], native_b["bundle_id"])
        self.assertNotEqual(sidecar_a["risk_envelope"]["sha256"], sidecar_b["risk_envelope"]["sha256"])
        self.assertNotEqual(sidecar_a["sidecar_id"], sidecar_b["sidecar_id"])

    def test_corrected_observation_is_distinct_not_historical_order(self):
        _, original, _ = self.compose()
        _, corrected, _ = self.compose(revision="corrected", correction={"note": "synthetic correction"})
        self.assertEqual(corrected["source_state"], "AVAILABLE")
        self.assertNotEqual(original["sidecar_id"], corrected["sidecar_id"])
        self.assertEqual(corrected["production_behavior"], "UNCHANGED")

    def test_native_null_expiry_and_explicit_earlier_expiry(self):
        native, sidecar, _ = self.compose()
        self.assertIsNone(native["stale_after"])
        self.assertEqual(sidecar["valid_until"], EXPIRY)
        _, short, _ = self.compose(stale_after="2026-09-28T13:30:00Z")
        self.assertEqual(short["source_state"], "UNAVAILABLE")
        self.assertIn("WINDOW_EXCEEDS_ENVELOPE_EXPIRY", short["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
