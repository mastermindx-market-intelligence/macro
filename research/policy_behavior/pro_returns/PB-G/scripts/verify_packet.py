#!/usr/bin/env python3
"""Verify the bounded PB-G research packet against immutable source artifacts.

This is an offline integrity/reproduction tool, not a production evaluator or a
test of causal identification, source completeness, live consumers or authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

PACKET = Path(__file__).resolve().parent.parent
F_MATRIX_BLOB = "bcd2a2d44d02b7796484f1bdc549a684816cc577"
F_COUNTS = {"SURVIVES": 95, "WEAKEN": 5, "REJECT": 13, "NEEDS_MORE_DATA": 9}
MAPPING = {
    "SURVIVES": "RETAIN_AS_QUALIFIED",
    "WEAKEN": "NARROW_AND_RETAIN",
    "REJECT": "REJECT_STRONG_FORM",
    "NEEDS_MORE_DATA": "UNRESOLVED",
}
PREFERRED = [
    "PB_G_INTEGRATED_FINDINGS.md", "PB_G_CLAIM_LEDGER.json",
    "PB_G_POLICY_BEHAVIOR_BASELINE.md", "PB_G_ARCHITECTURE_FREEZE.md",
    "PB_G_NO_DUPLICATION_MAP.md", "PB_G_BUILD_ROADMAP.md",
    "PB_G_IMPLEMENTATION_HANDOFF_INDEX.md",
]
BRIEFS = [
    "PBG_01_SOURCE_CLOCKS.md", "PBG_02_POLICY_BEHAVIOR_VIEW.md",
    "PBG_03_FINANCING_SUPPORT_DOSSIER.md", "PBG_04_US_JAPAN_CONSTRAINTS.md",
    "PBG_05_T2_INCUMBENT_INTERFACE.md", "PBG_06_ANNOUNCEMENT_PANEL.md",
    "PBG_07_EVALUATION_MATURITY.md",
]
ROW_FIELDS = {
    "id", "originating_lane", "claim_kind", "original_claim", "source_evidence",
    "source_locator", "pb_f", "pb_g", "sample_size", "pit_quality",
    "historical_or_prospective", "mechanism_identified", "product_relevance",
    "authority_relevance", "next_falsifier", "strongest_counterargument",
    "integration_boundary", "required_precision_repair",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def verify(source_dir: Path) -> dict:
    source_dir = source_dir.resolve()
    f_path = source_dir / "PB_F_CLAIM_MATRIX.json"
    require(f_path.is_file(), "Missing pinned PB-F matrix in source directory.")
    require(git_blob(f_path.read_bytes()) == F_MATRIX_BLOB, "PB-F matrix Git blob mismatch.")
    f = read_json(f_path)
    ledger = read_json(PACKET / "PB_G_CLAIM_LEDGER.json")
    manifest = read_json(PACKET / "PB_G_SOURCE_MANIFEST.json")
    f_rows = {x["id"]: x for x in f["claims"]}
    rows = ledger["claims"]
    require(len(f_rows) == len(f["claims"]) == len(rows) == 122, "Wrong claim denominator.")
    require(len({x["id"] for x in rows}) == 122, "Duplicate PB-G claim IDs.")
    require({x["id"] for x in rows} == set(f_rows), "Missing or extra claim IDs.")
    require(Counter(x["disposition"] for x in f_rows.values()) == F_COUNTS, "PB-F counts moved.")
    require(ledger["pb_f_disposition_counts"] == F_COUNTS, "Ledger PB-F summary changed.")
    require(ledger["research_only"] is True, "Research-only flag missing.")
    require(ledger["production_eligible"] is False, "Ledger production authority widened.")
    require(ledger["parent_program_complete"] is False, "Parent completion falsely asserted.")

    pins = {x["lane"]: x["head_sha"] for x in manifest["inputs"]}
    source_refs = 0
    for row in rows:
        cid = row["id"]
        original = f_rows[cid]
        require(ROW_FIELDS <= set(row), f"{cid}: required field missing.")
        require(row["original_claim"] == original["actual_claim"], f"{cid}: original claim changed.")
        require(row["source_evidence"] == original["evidence"], f"{cid}: original evidence changed.")
        require(row["pb_f"]["disposition"] == original["disposition"], f"{cid}: PB-F ruling changed.")
        require(row["pb_g"]["disposition"] == MAPPING[original["disposition"]], f"{cid}: wrong mapping.")
        require(isinstance(row["next_falsifier"], list) and row["next_falsifier"], f"{cid}: absent falsifier.")
        require(row["pb_g"]["confidence"]["is_calibrated_probability"] is False, f"{cid}: calibrated claim.")
        require(row["pit_quality"]["production_pit_admission"] is False, f"{cid}: PIT promotion.")
        require(row["pit_quality"]["prospective_observations_established"] is False, f"{cid}: enrollment.")
        for flag in ("production_eligible", "rank", "entry", "size", "trading", "live_alerts"):
            require(row["authority_relevance"][flag] is False, f"{cid}: authority flag {flag}.")
        for source in row["source_evidence"]:
            locator = re.fullmatch(
                r"https://github.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)",
                source["url"],
            )
            require(locator is not None, f"{cid}: source URL is not immutable.")
            repository, commit, path = locator.groups()
            require(source.get("commit", commit) == commit, f"{cid}: source commit mismatch.")
            require(source.get("repository", repository) == repository, f"{cid}: repository mismatch.")
            require(source.get("path", path) == path, f"{cid}: source path mismatch.")
            source_refs += 1

    g_counts = dict(Counter(x["pb_g"]["disposition"] for x in rows))
    require(g_counts == ledger["pb_g_disposition_counts"], "PB-G summary count mismatch.")
    by_id = {x["id"]: x for x in rows}
    require(by_id["D11"]["historical_or_prospective"] == "OPEN_HYPOTHESIS_WITH_HISTORICAL_CONTEXT", "D11 uncertainty lost.")
    require("CLOCK_REPAIR" in by_id["E26"]["pb_g"]["confidence"]["assessment"], "E26 repair qualification lost.")
    require("coded issuer" in by_id["C28"]["pb_g"]["qualified_interpretation"].lower(), "C28 exclusion broadened.")

    for filename in PREFERRED + ["PB_G_ACCEPTANCE.md", "PB_G_SOURCE_MANIFEST.json",
                                 "PB_G_BASELINE_SOURCE_RECEIPTS.json", "PB_G_CHECKPOINT.md"]:
        require((PACKET / filename).is_file(), "Missing file: " + filename)
    for filename in BRIEFS:
        path = PACKET / "handoffs" / filename
        require(path.is_file(), "Missing brief: " + filename)
        require("PROPOSED_UNLAUNCHED" in path.read_text(), "Brief dispatch state changed: " + filename)

    relative_links = 0
    for md in sorted(PACKET.rglob("*.md")):
        for target in re.findall(r"\]\(([^)]+)\)", md.read_text(encoding="utf-8")):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            dest = (md.parent / target).resolve()
            require(PACKET == dest or PACKET in dest.parents, "Local link escapes packet: " + target)
            # This receipt is the output of this verification; it may not exist on the first run.
            require(dest.is_file() or dest == PACKET / "PB_G_VERIFICATION.json", "Broken link: " + target)
            relative_links += 1

    owner_files = manifest["owner_census"]["files"]
    require(len(owner_files) == 43, "Owner census denominator changed.")
    require(len({x["path"] for x in owner_files}) == 43, "Duplicate owner census paths.")
    for entry in owner_files:
        require(re.fullmatch(r"[0-9a-f]{40}", entry["blob"]) is not None, "Owner blob not pinned.")
    reviewed_paths = {x["path"] for x in owner_files}
    moved_paths = {x["path"] for x in manifest["final_source_recheck"]["main_movement"]["files"]}
    require(not reviewed_paths.intersection(moved_paths), "Main movement intersects inspected owners.")
    for snapshot in manifest["final_source_recheck"]["source_returns"]:
        require(snapshot["head"] == pins[snapshot["key"]], "Research return head moved.")
        require(snapshot["merged"] is False, "Research input merge state changed.")
    require(manifest["final_source_recheck"]["protected_procedure"]["protected"] is True, "Procedure protection not established.")

    with tempfile.TemporaryDirectory(prefix="pb-g-reproduction-") as temp:
        result_path = Path(temp) / "recomputed.json"
        process = subprocess.run(
            [sys.executable, str(PACKET / "scripts/reproduce_baseline.py"),
             "--source-dir", str(source_dir), "--output", str(result_path)],
            text=True, capture_output=True, check=False,
        )
        require(process.returncode == 0, "Baseline reproduction failed: " + process.stderr[-2000:])
        require(result_path.read_bytes() == (PACKET / "PB_G_BASELINE_RECOMPUTED.json").read_bytes(),
                "Reproduced baseline bytes differ.")
    baseline = read_json(PACKET / "PB_G_BASELINE_RECOMPUTED.json")
    require(baseline["supplied_pilot_own_score_groups_exactly_reproduced"] == 60, "Wrong score-group count.")
    require(baseline["primary_count"] == 24 and baseline["separate_challenge_count"] == 1, "Challenge pooled.")
    require(baseline["target_outcome_mismatch_rows"] == [], "Unexpected target-label difference.")
    require(baseline["PB_B"]["abstention_count"] == 45 and baseline["PB_B"]["comparison_eligible_count"] == 0,
            "PB-B abstentions converted to forecasts.")
    require(len(baseline["PB_B"]["policy_target_cluster_counts"]) == 10, "PB-B target denominator changed.")
    require(baseline["PB_E"]["structural_dossier_count"] == 15 and baseline["PB_E"]["edge_count"] == 112,
            "PB-E denominator changed.")
    require(baseline["denominator_ruling"]["rich_M2_scored_episodes"] == 0, "Rich M2 falsely scored.")
    require(baseline["denominator_ruling"]["supported_40_to_60_comparable_baseline"] is False, "Incompatible records pooled.")
    for target in baseline["primary"].values():
        for horizon, result in target.items():
            pair = result["pairwise_common_coverage"]["M0__M2"]
            require(pair["count"] == 8, "Wrong M0/M2 common sample.")
            require(pair["direction_disagreement_ids"] == [], "M0/M2 predictions no longer identical.")
            expected = {"1": 4, "3": 7, "6": 5}[horizon]
            for model in ("M0", "M2"):
                require(pair["models"][model]["correct_count"] == expected, "Matched score changed.")
            require(result["all_three_common_coverage"]["count"] == 4, "Wrong three-model denominator.")

    digest = hashlib.sha256((PACKET / "PB_G_BASELINE_RECOMPUTED.json").read_bytes()).hexdigest()
    require(digest == manifest["baseline"]["output_sha256"], "Baseline output digest differs from manifest.")
    return {
        "schema": "pb_g_offline_verification.v1",
        "status": "PASS",
        "scope": "Offline claim/source integrity and frozen arithmetic only; no production or causal validation.",
        "claim_count": 122,
        "pb_f_matrix_git_blob_sha": F_MATRIX_BLOB,
        "original_claims_evidence_and_dispositions_preserved": True,
        "pb_f_counts": F_COUNTS,
        "pb_g_counts": g_counts,
        "source_evidence_references_checked": source_refs,
        "all_authority_and_pit_promotion_flags_false": True,
        "next_falsifiers_all_nonempty_arrays": True,
        "preferred_files_present": len(PREFERRED),
        "future_briefs_unlaunched": len(BRIEFS),
        "relative_markdown_file_links_checked": relative_links,
        "owner_source_paths_pinned": len(owner_files),
        "research_source_heads_unchanged": len(pins),
        "source_files_git_blob_verified_by_reproduction": 18,
        "supplied_own_score_groups_reproduced": 60,
        "recomputed_output_byte_identical": True,
        "recomputed_output_sha256": digest,
        "primary_episodes": 24,
        "separate_challenge": 1,
        "m0_m2_min_common": 8,
        "all_three_common": 4,
        "rich_m2_scored": 0,
        "b_scored": 0,
        "forty_to_sixty_comparable_baseline_complete": False,
        "precise_insufficiency_verified": True,
        "parent_program_complete": False,
        "hosted_ci_or_production_proof_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.source_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
