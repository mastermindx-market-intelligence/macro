"""Pure research-only ROR-1 artifact-boundary verification tests.

Tests characterize displayed source discontinuities. They do not create an
alert, inspect protected endpoints, or declare which pipeline has authority.
"""
from __future__ import annotations

from copy import deepcopy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_artifact_consistency import audit, AuditError


def artifacts():
    """MINIMIZED fixture matching source fields read at Oct15 current Macro main."""
    return {
        "site_envelope": {
            "schema": "mastermind.risk_envelope/v1",
            "source_session": "2026-10-14",
            "produced_at": "2026-10-15T04:51:27Z",
            "revision": "settled", "data_state": "PARTIAL",
            "hazard_summary": {
                "stage": None, "stage_reason": "required_source_state_unmapped",
                "unmapped_required_sources": ["leadership-crack-latest"]
            },
            "provenance": {"sources": [{
                "source_id": "leadership-crack-latest",
                "state": "CRACKING", "coverage": "FRESH",
                "as_of": "2026-10-14", "role": "hazard_evidence",
                "stage_ceiling": "FRAGILE",
                "detail": {"dislocation": True, "n_fresh": 42, "n_total": 42},
            }]},
            "measured_state": {"as_of": "2026-10-14", "score": 44, "verdict": "MIXED"},
        },
        "data_envelope": {
            "schema": "mastermind.risk_envelope/v1",
            "source_session": "2026-10-13",
            "produced_at": "2026-10-14T19:32:18Z",
            "data_state": "DEGRADED",
            "hazard_summary": {"stage": None, "stage_reason": "required_coverage_unavailable"},
        },
        "market_state": {
            "asof": "2026-10-14", "score": 44, "verdict": "MIXED",
            "freshness": {"any_input_stale": True, "stale_inputs": ["hy_oas","ofr_fsi","pct_above_200","us10y"]},
        },
        "leadership": {"asof": "2026-10-08", "state": "INTACT", "n_fresh": 42},
        "market_plane": {
            "schema": "neuralweb.market_plane.v1", "asof": "2026-10-14",
            "produced_at": "2026-10-14T19:35:57Z",
            "verdict": {"score": 50, "verdict": "MIXED"}, "stale": False,
            "is_context_only": True,
        },
    }


class ArtifactConsistencyTests(unittest.TestCase):
    def test_native_cracking_was_lost_by_source_stage_mapper(self):
        a = audit(artifacts())
        problems = {x["code"]: x for x in a["findings"]}
        self.assertIn("UNMAPPED_FRESH_REQUIRED_HAZARD", problems)
        p = problems["UNMAPPED_FRESH_REQUIRED_HAZARD"]
        self.assertEqual(p["classification"], "confirmed_in_published_artifact")
        self.assertEqual(p["source_session"], "2026-10-14")
        self.assertEqual(p["source_state"], "CRACKING")
        self.assertEqual(p["source_stage_ceiling"], "FRAGILE")
        self.assertFalse(p["asserts_contagion"])

    def test_variant_dates_report_disagreement_not_causal_failure(self):
        a = audit(artifacts())
        bycode = {x["code"]: x for x in a["findings"]}
        self.assertEqual(bycode["ENVELOPE_SESSION_DIVERGENCE"]["classification"], "publication_variants_need_consumer_binding")
        self.assertEqual(bycode["LEADERSHIP_SESSION_DIVERGENCE"]["classification"], "publication_variants_need_source_binding")
        self.assertEqual(bycode["MARKET_PLANE_SCORE_DIVERGENCE"]["classification"], "different_generation_clocks_no_issue_time_inference")

    def test_fixing_the_mapping_removes_only_unmapped_warning(self):
        d = artifacts()
        d["site_envelope"]["hazard_summary"] = {"stage": "FRAGILE", "stage_reason": "observed",
                                                  "unmapped_required_sources": []}
        a = audit(d)
        codes = {x["code"] for x in a["findings"]}
        self.assertNotIn("UNMAPPED_FRESH_REQUIRED_HAZARD", codes)
        self.assertIn("ENVELOPE_SESSION_DIVERGENCE", codes)

    def test_stale_required_source_is_not_a_fresh_unmapped_warning(self):
        d = artifacts()
        d["site_envelope"]["provenance"]["sources"][0]["coverage"] = "STALE"
        a = audit(d)
        self.assertNotIn("UNMAPPED_FRESH_REQUIRED_HAZARD", {x["code"] for x in a["findings"]})

    def test_missing_docs_are_unknown_not_calm(self):
        d = artifacts()
        d["site_envelope"] = None
        a = audit(d)
        self.assertEqual(a["status"], "INCOMPLETE")
        self.assertIn("SITE_ENVELOPE_MISSING", {x["code"] for x in a["findings"]})

    def test_native_verdict_date_is_lost_by_compact_plane(self):
        d = artifacts()
        d["world_state"] = {
            "produced_at": "2026-10-14T19:32:19Z",
            "verdict": {"asof": "2026-10-13", "score": 50,
                        "freshness": {"any_input_stale": True}},
        }
        result = audit(d)
        matches = [x for x in result["findings"]
                   if x["code"] == "VERDICT_SOURCE_SESSION_LOST"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["native_verdict_session"], "2026-10-13")
        self.assertEqual(matches[0]["plane_label_session"], "2026-10-14")
        self.assertEqual(matches[0]["classification"], "confirmed_source_date_not_projected")
        self.assertFalse(matches[0]["asserts_stale_at_production"])

    def test_native_verdict_source_date_carried_means_no_loss(self):
        d = artifacts()
        d["world_state"] = {"produced_at": "2026-10-14T19:32:19Z",
                            "verdict": {"asof": "2026-10-13", "score": 50}}
        d["market_plane"]["verdict"]["source_session"] = "2026-10-13"
        self.assertNotIn("VERDICT_SOURCE_SESSION_LOST",
                         {x["code"] for x in audit(d)["findings"]})

    def test_source_health_remains_independent_of_market_score(self):
        a = audit(artifacts())
        codes = {x["code"] for x in a["findings"]}
        self.assertIn("MARKET_STATE_INPUTS_STALE", codes)
        self.assertNotIn("SCORING_RECOMMENDATION", codes)
        self.assertNotIn("trade", a)
        self.assertNotIn("new_verdict", a)

    def test_session_date_and_numeric_values_validate(self):
        d = artifacts()
        d["site_envelope"]["source_session"] = "2026-13-45"
        with self.assertRaises(AuditError):
            audit(d)
        d = artifacts()
        d["market_state"]["score"] = float("nan")
        with self.assertRaises(AuditError):
            audit(d)

    def test_output_is_stable_and_does_not_mutate_sources(self):
        d = artifacts()
        orig = deepcopy(d)
        self.assertEqual(audit(d), audit(d))
        self.assertEqual(d, orig)

    def test_cli_replays_saved_minimal_bundle(self):
        import json
        import subprocess
        import tempfile
        bundle = {
            "schema": "ror1.grounded_artifact_excerpt.v1",
            "macro_commit": "1b12af09222df183ac61ed5bcabb1ecc6bf5c735",
            "observations": artifacts(),
            "sources": {"site/riskdata/risk_envelope.json": {
                "blob_sha": "80a2dd2f86a62944803cd3224d448e5ba1eebd76"
            }},
        }
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "bundle.json"
            file.write_text(json.dumps(bundle), encoding="utf-8")
            run = subprocess.run([
                sys.executable, str(Path(__file__).with_name("audit_artifact_consistency.py")),
                "--bundle", str(file),
            ], capture_output=True, text=True, timeout=6)
        self.assertEqual(run.returncode, 0, run.stderr)
        replay = json.loads(run.stdout)
        self.assertEqual(replay["macro_commit"], bundle["macro_commit"])
        self.assertEqual(replay["audit"], audit(artifacts()))
        self.assertIn("inputs_sha256", replay)
        self.assertEqual(replay["sources"], bundle["sources"])

    def test_cli_refuses_unrecognized_bundle_schema(self):
        import json
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "bundle.json"
            file.write_text(json.dumps({"schema": "unknown.v1",
                                        "observations": artifacts()}), encoding="utf-8")
            run = subprocess.run([
                sys.executable, str(Path(__file__).with_name("audit_artifact_consistency.py")),
                "--bundle", str(file),
            ], capture_output=True, text=True, timeout=6)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("invalid_bundle_schema", run.stderr)


if __name__ == "__main__":
    unittest.main()
