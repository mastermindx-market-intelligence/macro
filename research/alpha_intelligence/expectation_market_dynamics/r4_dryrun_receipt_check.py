#!/usr/bin/env python3
"""Check an R4 descriptive-coupling dry-run receipt. Standard library only."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = "itp.r4_descriptive_coupling_dryrun_receipt.v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STAGES = ("EXP-1", "MKT-1", "CPL-1")
COLLECTIONS = ("C1", "C2")
HEADS = {
    "exp1": "13910854fbd652dcdf975301bdc8c6728c2e4767",
    "mkt1": "314ddae3f926c4ab1e424c646b1f21e90b2c6a68",
    "cpl1": "3bf903fae36b94cff461eca81a9538862ec0cc38",
}
ROOT_KEYS = (
    "schema", "composition", "collections", "prereg", "materialized_paths",
    "stages", "coupling_states", "missingness", "honest_n", "comparators",
    "gaps", "authority", "financial_influence", "k3e_admissible",
)


def _violations(doc: object) -> list[str]:
    found: list[str] = []

    def need(ok: bool, message: str) -> None:
        if not ok:
            found.append(message)

    need(isinstance(doc, dict), "root is not an object")
    if not isinstance(doc, dict):
        return found
    for key in ROOT_KEYS:
        need(key in doc, f"missing key {key}")
    need(doc.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    need(doc.get("authority") == "descriptive_dry_run_only",
         "authority must be descriptive_dry_run_only")
    need(doc.get("financial_influence") is False, "financial_influence must be false")
    need(doc.get("k3e_admissible") is False, "k3e_admissible must be false")

    composition = doc.get("composition")
    need(isinstance(composition, dict), "composition must be an object")
    if isinstance(composition, dict):
        need(isinstance(composition.get("main_sha"), str)
             and bool(HEX40.fullmatch(composition.get("main_sha", ""))),
             "composition.main_sha must be 40 hex characters")
        heads = composition.get("heads")
        need(isinstance(heads, dict), "composition.heads must be an object")
        if isinstance(heads, dict):
            for name, sha in HEADS.items():
                need(heads.get(name) == sha, f"composition.heads.{name} must be {sha}")
        conflicts = composition.get("conflicts_resolved")
        need(isinstance(conflicts, list)
             and all(isinstance(item, str) and item for item in conflicts),
             "composition.conflicts_resolved must be a list of non-empty strings")
        need(isinstance(composition.get("composite_tree_sha"), str)
             and bool(HEX40.fullmatch(composition.get("composite_tree_sha", ""))),
             "composition.composite_tree_sha must be 40 hex characters")

    collections = doc.get("collections")
    need(isinstance(collections, dict), "collections must be an object")
    if isinstance(collections, dict):
        for name in COLLECTIONS:
            item = collections.get(name)
            need(isinstance(item, dict), f"collections.{name} must be an object")
            if not isinstance(item, dict):
                continue
            need(isinstance(item.get("commit"), str)
                 and bool(HEX40.fullmatch(item.get("commit", ""))),
                 f"collections.{name}.commit must be 40 hex characters")
            blobs = item.get("input_blobs")
            need(isinstance(blobs, dict) and bool(blobs),
                 f"collections.{name}.input_blobs must be a non-empty object")
            if isinstance(blobs, dict):
                for path, blob in blobs.items():
                    need(isinstance(path, str) and bool(path)
                         and isinstance(blob, str) and bool(HEX40.fullmatch(blob)),
                         f"collections.{name}.input_blobs[{path!r}] must be a 40-hex blob")

    prereg = doc.get("prereg")
    need(isinstance(prereg, dict), "prereg must be an object")
    if isinstance(prereg, dict):
        need(isinstance(prereg.get("registration_id"), str)
             and bool(prereg.get("registration_id")),
             "prereg.registration_id must be a non-empty string")
        for key in ("expected_digest", "recomputed_digest"):
            need(isinstance(prereg.get(key), str)
                 and bool(HEX64.fullmatch(prereg.get(key, ""))),
                 f"prereg.{key} must be 64 hex characters")
        need(isinstance(prereg.get("match"), bool), "prereg.match must be a boolean")

    paths = doc.get("materialized_paths")
    need(isinstance(paths, list), "materialized_paths must be a list")
    if isinstance(paths, list):
        for index, item in enumerate(paths):
            need(isinstance(item, dict), f"materialized_paths[{index}] must be an object")
            if not isinstance(item, dict):
                continue
            for key in ("path", "from_commit", "blob_sha"):
                need(isinstance(item.get(key), str) and bool(item.get(key)),
                     f"materialized_paths[{index}].{key} must be a non-empty string")

    stages = doc.get("stages")
    need(isinstance(stages, list), "stages must be a list")
    seen: set[tuple[str, str]] = set()
    if isinstance(stages, list):
        for index, stage in enumerate(stages):
            prefix = f"stages[{index}]"
            need(isinstance(stage, dict), f"{prefix} must be an object")
            if not isinstance(stage, dict):
                continue
            kind = stage.get("stage")
            collection = stage.get("collection")
            status = stage.get("status")
            need(kind in STAGES, f"{prefix}.stage must be EXP-1, MKT-1, or CPL-1")
            need(collection in COLLECTIONS, f"{prefix}.collection must be C1 or C2")
            if kind in STAGES and collection in COLLECTIONS:
                pair = (kind, collection)
                need(pair not in seen, f"duplicate stage {kind} {collection}")
                seen.add(pair)
            need(isinstance(stage.get("command"), str) and bool(stage.get("command")),
                 f"{prefix}.command must be a non-empty string")
            need(isinstance(stage.get("rows_in"), int) and not isinstance(stage.get("rows_in"), bool)
                 and stage.get("rows_in") >= 0, f"{prefix}.rows_in must be a non-negative integer")
            need(isinstance(stage.get("rows_out"), int) and not isinstance(stage.get("rows_out"), bool)
                 and stage.get("rows_out") >= 0, f"{prefix}.rows_out must be a non-negative integer")
            refusals = stage.get("refusal_counts")
            need(isinstance(refusals, dict), f"{prefix}.refusal_counts must be an object")
            if isinstance(refusals, dict):
                for code, count in refusals.items():
                    need(isinstance(code, str) and bool(code)
                         and isinstance(count, int) and not isinstance(count, bool) and count >= 0,
                         f"{prefix}.refusal_counts[{code!r}] must be a non-negative integer")
            if status == "RAN":
                for key in ("input_sha256", "output_sha256"):
                    need(isinstance(stage.get(key), str)
                         and bool(HEX64.fullmatch(stage.get(key, ""))),
                         f"{prefix}.{key} must be 64 hex characters when status is RAN")
                need(not stage.get("error"), f"{prefix}.error must be empty when status is RAN")
            elif status == "GAP":
                need(isinstance(stage.get("error"), str) and bool(stage.get("error").strip()),
                     f"{prefix}.error must be a non-empty string when status is GAP")
            else:
                need(False, f"{prefix}.status must be RAN or GAP")
        for kind in STAGES:
            for collection in COLLECTIONS:
                need((kind, collection) in seen, f"missing stage {kind} {collection}")

    coupling = doc.get("coupling_states")
    need(isinstance(coupling, dict), "coupling_states must be an object")
    if isinstance(coupling, dict):
        for name in COLLECTIONS:
            counts = coupling.get(name)
            need(isinstance(counts, dict), f"coupling_states.{name} must be an object")
            if isinstance(counts, dict):
                for state, count in counts.items():
                    need(isinstance(state, str) and bool(state)
                         and isinstance(count, int) and not isinstance(count, bool) and count >= 0,
                         f"coupling_states.{name}[{state!r}] must be a non-negative integer")

    missingness = doc.get("missingness")
    need(isinstance(missingness, dict) and bool(missingness),
         "missingness must be a non-empty object")
    if isinstance(missingness, dict):
        for field, item in missingness.items():
            ok = (isinstance(item, dict)
                  and isinstance(item.get("missing"), int)
                  and not isinstance(item.get("missing"), bool)
                  and isinstance(item.get("total"), int)
                  and not isinstance(item.get("total"), bool)
                  and 0 <= item.get("missing") <= item.get("total"))
            need(ok, f"missingness[{field!r}] must be {{missing, total}} with 0 <= missing <= total")

    honest = doc.get("honest_n")
    need(isinstance(honest, dict), "honest_n must be an object")
    if isinstance(honest, dict):
        for key in ("episodes_distinct", "rows", "tickers"):
            need(isinstance(honest.get(key), int) and not isinstance(honest.get(key), bool)
                 and honest.get(key) >= 0, f"honest_n.{key} must be a non-negative integer")
        need(isinstance(honest.get("rule"), str) and "episode_identity" in honest.get("rule", "")
             and "raw_row_count_may_substitute" in honest.get("rule", ""),
             "honest_n.rule must quote the prereg episode_law identity and row-substitution fields")

    comparators = doc.get("comparators")
    need(isinstance(comparators, list) and bool(comparators),
         "comparators must be a non-empty list")
    if isinstance(comparators, list):
        seen_ids: set[str] = set()
        for index, item in enumerate(comparators):
            prefix = f"comparators[{index}]"
            need(isinstance(item, dict), f"{prefix} must be an object")
            if not isinstance(item, dict):
                continue
            baseline = item.get("baseline_id")
            need(isinstance(baseline, str) and bool(baseline), f"{prefix}.baseline_id must be a non-empty string")
            if isinstance(baseline, str):
                need(baseline not in seen_ids, f"duplicate comparator {baseline}")
                seen_ids.add(baseline)
            need(isinstance(item.get("computed"), bool), f"{prefix}.computed must be a boolean")
            reason = item.get("value_or_reason")
            if item.get("computed") is False:
                need(isinstance(reason, str) and bool(reason.strip()),
                     f"{prefix}.value_or_reason must be a non-empty reason when computed is false")
            else:
                need(reason is not None, f"{prefix}.value_or_reason is required")

    gaps = doc.get("gaps")
    need(isinstance(gaps, list), "gaps must be a list")
    if isinstance(gaps, list):
        for index, item in enumerate(gaps):
            prefix = f"gaps[{index}]"
            need(isinstance(item, dict), f"{prefix} must be an object")
            if not isinstance(item, dict):
                continue
            for key in ("id", "stage", "what", "exact_command", "exact_error"):
                need(isinstance(item.get(key), str) and bool(item.get(key).strip()),
                     f"{prefix}.{key} must be a non-empty string")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", required=True, help="Path to the receipt JSON")
    args = parser.parse_args(argv)
    path = Path(args.check)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable receipt: {exc}")
        return 1
    found = _violations(doc)
    if found:
        for item in found:
            print(item)
        return 1
    stages = doc["stages"]
    ran = sum(1 for stage in stages if stage.get("status") == "RAN")
    gap = sum(1 for stage in stages if stage.get("status") == "GAP")
    print(f"ok {path.name}: stages={len(stages)} ran={ran} gap={gap} "
          f"financial_influence=false k3e_admissible=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
