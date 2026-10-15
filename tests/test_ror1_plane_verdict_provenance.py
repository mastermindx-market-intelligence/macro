"""ROR-1 native producer regression — display-only verdict clock and data health.

The tested production module is imported directly from the declared Macro root,
never from an extracted/transcribed function. All fixture files are in a
temporary directory, and no producer or live artifact is written.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from engine.neuralweb.mastermind_context import build_market_plane  # noqa: E402

NOW = datetime(2026, 10, 14, 20, 0, tzinfo=timezone.utc)


def build(world):
    with tempfile.TemporaryDirectory(prefix="ror1-plane-fixture-") as dirname:
        root = Path(dirname)
        directory = root / "data" / "neuralweb"
        directory.mkdir(parents=True)
        (directory / "world_state.json").write_text(json.dumps(world))
        return build_market_plane(root=root, now=NOW)


class NativePlaneVerdictClock(unittest.TestCase):
    def test_explicit_native_verdict_session_survives_processing_date(self):
        d = build({
            "produced_at": "2026-10-14T19:32:19Z",
            "verdict": {
                "verdict": "MIXED", "score": 50,
                "label_en": "Mixed", "label_zh": "混合",
                "asof": "2026-10-13",
                "freshness": {
                    "any_input_stale": True,
                    "data_asof": "2026-10-13",
                    "expected_asof": "2026-10-13",
                },
            },
        })
        # Preserve existing processing-date contract; do not silently change
        # aggregate staleness or assert that a pre-close settled value was stale.
        self.assertEqual(d["asof"], "2026-10-14")
        self.assertFalse(d["stale"])
        self.assertEqual(d["verdict"]["score"], 50)
        self.assertEqual(d["verdict"]["source_session"], "2026-10-13")
        self.assertEqual(d["verdict"]["source_freshness"], {
            "any_input_stale": True,
            "data_asof": "2026-10-13",
            "expected_asof": "2026-10-13",
        })
        self.assertTrue(d["is_context_only"])

    def test_healthy_input_receipt_is_preserved_as_false_only_if_explicit(self):
        d = build({
            "as_of": "2026-10-14",
            "verdict": {
                "asof": "2026-10-14",
                "score": 44, "verdict": "MIXED",
                "freshness": {
                    "any_input_stale": False,
                    "data_asof": "2026-10-14",
                    "expected_asof": "2026-10-14",
                },
            },
        })
        self.assertEqual(d["verdict"]["source_session"], "2026-10-14")
        self.assertIs(d["verdict"]["source_freshness"]["any_input_stale"], False)

    def test_unknown_freshness_is_not_synthesized_as_fresh(self):
        d = build({"produced_at": "2026-10-14T19:32:19Z",
                   "verdict": {"asof": "2026-10-13", "score": 50}})
        self.assertEqual(d["verdict"]["source_session"], "2026-10-13")
        self.assertIsNone(d["verdict"]["source_freshness"]["any_input_stale"])
        self.assertIsNone(d["verdict"]["source_freshness"]["data_asof"])
        self.assertIsNone(d["verdict"]["source_freshness"]["expected_asof"])

    def test_invalid_native_dates_never_become_valid_provenance(self):
        for invalid in ("2026-13-14", "2026-10-1", "", None, "2026-10-13T11:00:00Z"):
            with self.subTest(invalid=invalid):
                d = build({"produced_at": "2026-10-14T19:32:19Z",
                           "verdict": {"asof": invalid, "score": 50,
                                       "freshness": {
                                           "any_input_stale": "false",
                                           "data_asof": "no date",
                                           "expected_asof": "2026-10-14T00:00:00Z",
                                       }}})
                self.assertIsNone(d["verdict"]["source_session"])
                self.assertEqual(d["verdict"]["source_freshness"], {
                    "any_input_stale": None,
                    "data_asof": None,
                    "expected_asof": None,
                })

    def test_absent_source_remains_unknown_no_market_authority(self):
        d = build({})
        self.assertIsNone(d["verdict"]["source_session"])
        self.assertIsNone(d["verdict"]["source_freshness"]["any_input_stale"])
        self.assertTrue(d["stale"])
        self.assertTrue(d["is_context_only"])
        self.assertNotIn("may_execute", d["verdict"])
        self.assertNotIn("may_gate", d["verdict"])


if __name__ == "__main__":
    unittest.main()
