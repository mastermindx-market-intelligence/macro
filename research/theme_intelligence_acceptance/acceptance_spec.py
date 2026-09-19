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
    _require(result["checks"]["watch_invalidation"]["status"] == "FAIL", "WATCH false invalidation escaped")
    _require(result["checks"]["lane_matrix"]["status"] == "FAIL", "PRECIPICE semantic defect escaped")
    _require(
        result["checks"]["lane_matrix"]["failed_case_ids"] == ["clean_precipice_is_early"],
        "unexpected lane-matrix failure set",
    )
    _require(result["checks"]["published_path_consistency"]["status"] == "PASS", "real path did not reproduce")
    _require(result["checks"]["authority_invariance"]["status"] == "PASS", "authority changed on frozen subject")
    _require(len(result["inputs"]) == 8, "immutable input manifest is incomplete")

    mutations = harness.run_mutation_suite(ROOT, SUBJECT, CASES)
    expected = {
        "false_watch_green_without_transition",
        "fired_priority_removed",
        "high_crowding_priority_removed",
        "published_card_lane_mismatch",
        "published_falsifier_state_mismatch",
        "rank_authority_enabled",
        "clean_precipice_repair_discriminator",
    }
    observed = {row["id"] for row in mutations["mutations"]}
    _require(observed == expected, f"mutation set mismatch: {sorted(observed)}")
    _require(all(row["killed"] for row in mutations["mutations"]), "one or more false-green mutations survived")

    receipt = {
        "schema": "theme_intelligence.acceptance_spec_result.v1",
        "subject": SUBJECT,
        "baseline_product_verdict": result["product_verdict"],
        "baseline_failed_checks": result["failed_checks"],
        "mutation_count": len(mutations["mutations"]),
        "mutations_killed": sum(1 for row in mutations["mutations"] if row["killed"]),
        "status": "PASS",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
