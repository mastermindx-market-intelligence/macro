#!/usr/bin/env python3
"""Executable specification for the Lane F Theme Intelligence acceptance harness.

This is deliberately an explicit research command rather than a dark pytest suite.
Lane A owns the single shared CI-wiring change for the six-lane package.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.theme_intelligence_acceptance import harness  # noqa: E402


CASES = Path(__file__).with_name("incident_cases.v1.json")
SUBJECT = "68f80a8edf78966a3a89e1294038654944e9c217"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    result = harness.evaluate(ROOT, SUBJECT, CASES)

    _require(result["subject"]["commit"] == SUBJECT, "subject commit drifted")
    _require(result["product_verdict"] == "REJECTED_CURRENT_SOURCE", "known defects were not rejected")
    _require(
        result["failed_checks"] == [
            "watch_invalidation",
            "lane_matrix",
            "real_precipice_path",
        ],
        f"unexpected baseline failure set: {result['failed_checks']}",
    )
    _require(result["checks"]["watch_invalidation"]["status"] == "FAIL", "WATCH false invalidation escaped")
    _require(result["checks"]["lane_matrix"]["status"] == "FAIL", "PRECIPICE semantic defect escaped")
    _require(
        result["checks"]["lane_matrix"]["failed_case_ids"] == ["clean_precipice_is_early"],
        "unexpected lane-matrix failure set",
    )
    real = result["checks"]["real_precipice_path"]
    _require(real["status"] == "FAIL", "real Medical Devices PRECIPICE path escaped")
    _require(real["assertions"]["classifier_matches_lane_artifact"], "real classifier/artifact path drifted")
    _require(real["assertions"]["lane_artifact_matches_served_card"], "real artifact/card path drifted")
    _require(real["actual"]["crowding_band"] == "med", "real medium-crowding discriminator drifted")
    _require(real["actual"]["divergence"] is None, "real no-divergence discriminator drifted")
    _require(result["checks"]["artifact_health"]["status"] == "PASS", "artifact clocks/stale/null health failed")
    _require(result["checks"]["published_path_consistency"]["status"] == "PASS", "WATCH real path did not reproduce")
    _require(result["checks"]["authority_invariance"]["status"] == "PASS", "authority changed on frozen subject")
    _require(len(result["inputs"]) == 10, "immutable input manifest is incomplete")
    _require(
        result["contract_gates"]["rerating_lane_interpretation"]["state"]
        == "LANE_A_ADJUDICATION_REQUIRED",
        "RE-RATING contract gate was silently resolved",
    )

    mutations = harness.run_mutation_suite(ROOT, SUBJECT, CASES)
    expected = {
        "false_watch_green_without_transition",
        "fired_priority_removed",
        "high_crowding_priority_removed",
        "published_card_lane_mismatch",
        "published_falsifier_state_mismatch",
        "rank_authority_enabled",
        "known_defect_repair_candidate",
        "partial_precipice_repair_only",
        "foresight_asof_dropped",
        "stale_null_coerced_to_low_zero",
        "theme_state_mixed_generation",
    }
    observed = {row["id"] for row in mutations["mutations"]}
    _require(observed == expected, f"mutation set mismatch: {sorted(observed)}")
    _require(all(row["killed"] for row in mutations["mutations"]), "one or more false-green mutations survived")

    receipt = {
        "schema": "theme_intelligence.acceptance_spec_result.v2",
        "subject": SUBJECT,
        "baseline_product_verdict": result["product_verdict"],
        "baseline_failed_checks": result["failed_checks"],
        "baseline_defect_ids": [
            "WATCH_WITHOUT_TRANSITION_EVIDENCE",
            "PRECIPICE_FORCED_TO_CAUTION",
        ],
        "contract_gates": result["contract_gates"],
        "mutation_count": len(mutations["mutations"]),
        "mutations_killed": sum(1 for row in mutations["mutations"] if row["killed"]),
        "status": "PASS",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
