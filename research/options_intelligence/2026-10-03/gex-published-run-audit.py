#!/usr/bin/env python3
"""Fit-free replay of one pinned published C1 board; no provider or production effects.

The adjacent fusion source is an exact immutable source copy, verified before import.
Input rows retain only the published raw fields consumed by that source and score receipts.
This audits the fusion member on this pool; it does not reconstruct upstream selection.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from collections import Counter

SOURCE_BLOB = "210e070103b36f10bbbf19981420a17bb9fdc4fc"
MEMBER = "gex_confirm_verdict"
FAMILY = "F5_FLOW_POSITIONING"
STAGE_ORDER = ("live", "setting_up", "ran", "basing", "blocked")


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_source(path: Path):
    if git_blob(path.read_bytes()) != SOURCE_BLOB:
        raise ValueError("Pinned fusion source identity mismatch")
    spec = importlib.util.spec_from_file_location("options_audit_pinned_fusion", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def ranks(rows: list[dict], scores: list[float | None]) -> list[int]:
    stage_rank = {stage: i for i, stage in enumerate(STAGE_ORDER)}
    def key(i):
        published = None if scores[i] is None else round(scores[i], 1)
        return (stage_rank.get(rows[i]["stage"], len(STAGE_ORDER)),
                published is None, -(published or 0.0), rows[i]["ticker"])
    answer = [0] * len(rows)
    for rank, i in enumerate(sorted(range(len(rows)), key=key), 1):
        answer[i] = rank
    return answer


def comparison(rows, full_scores, other_scores):
    full_ranks = ranks(rows, full_scores)
    other_ranks = ranks(rows, other_scores)
    delta = [abs(a-b) for a,b in zip(full_ranks, other_ranks)]
    before = {r["ticker"] for r,rank in zip(rows, full_ranks) if rank <= 30}
    after = {r["ticker"] for r,rank in zip(rows, other_ranks) if rank <= 30}
    return {
        "rows_with_changed_raw_score": sum(a != b for a,b in zip(full_scores, other_scores)),
        "rows_with_changed_published_score": sum(
            (None if a is None else round(a,1)) != (None if b is None else round(b,1))
            for a,b in zip(full_scores,other_scores)),
        "rows_moved": sum(d != 0 for d in delta),
        "mean_abs_rank_displacement": sum(delta)/len(delta),
        "max_abs_rank_displacement": max(delta),
        "top30_names_replaced": len(before-after),
        "top30_symmetric_difference": len(before ^ after),
        "top30_removed": sorted(before-after),
        "top30_added": sorted(after-before),
    }


def audit(base: Path) -> dict:
    source_path = base / "gex-audit-fusion-source.py"
    input_path = base / "gex-published-board-extract.json"
    archived_path = base / "gex-w3-archived-coverage.json"
    f = load_source(source_path)
    board = json.loads(input_path.read_text())
    archived = json.loads(archived_path.read_text())
    rows = board["buy"]
    assert board["ranking"]["definition"] == "us_prophet_v3"
    assert tuple(board["ranking"]["stage_order"]) == STAGE_ORDER
    assert len({r["ticker"] for r in rows}) == len(rows)
    assert sorted(r["score_rank"] for r in rows) == list(range(1,len(rows)+1))
    plane = f.fuse_board(rows)
    observed = [r["prophet"]["score"] for r in rows]
    reproduced = [None if s is None else round(s,1) for s in plane.scores]
    assert reproduced == observed, "Published score replay mismatch"
    full_ranks = ranks(rows, plane.scores)
    assert full_ranks == [r["score_rank"] for r in rows], "Published rank replay mismatch"
    stored = board["ranking"]["fusion"]
    assert list(plane.admission.admitted) == stored["w3_structural"]["admitted_frozen"]
    assert plane.members_dropped == stored["floors"]["members_stood_down"]
    assert plane.members_collapsed == stored["floors"]["members_collapsed_as_duplicates"]
    assert plane.families_present == stored["families_active"]
    for i,row in enumerate(rows):
        display = row["prophet"]["fusion"]
        assert {k:round(v,6) for k,v in plane.member_percentiles[i].items()} == display["member_percentiles"]
        assert {k:round(v*100,2) for k,v in plane.family_scores[i].items()} == display["family_contribution"]
        assert len(plane.family_scores[i]) == display["n_families"]
    members = list(plane.extracted_members)
    values = [f.oriented_value(r[MEMBER], f.REGISTERED_SIGNS[MEMBER]) for r in members]
    nonnull = [v for v in values if v is not None]
    raw_counts = Counter("missing" if r[MEMBER] is None else r[MEMBER] for r in members)
    # Remove only this member from the already-frozen admitted set. Do not reselect
    # the cohort, refit models, relax floors or interpret the result as a return effect.
    without = f.aggregate(members, [m for m in plane.admission.admitted if m != MEMBER])
    no_gex = comparison(rows, plane.scores, without.scores)
    assert MEMBER not in plane.admission.admitted
    assert no_gex["rows_with_changed_raw_score"] == no_gex["rows_moved"] == 0
    # Whole-family deletion is different; use exact in-memory values, not the rounded
    # display contributions, and compare to the producer's own stored LOFO diagnostic.
    family_removed = [{k:v for k,v in s.items() if k != FAMILY} for s in plane.family_scores]
    family_scores = [sum(s.values())/len(s)*100 if s else None for s in family_removed]
    no_f5 = comparison(rows, plane.scores, family_scores)
    published_lofo = next(x for x in stored["w3_structural"]["lofo"] if x["family"] == FAMILY)
    for key in ("rows_moved", "max_abs_rank_displacement", "mean_abs_rank_displacement"):
        assert math.isclose(no_f5[key], published_lofo[key], rel_tol=0, abs_tol=1e-12)
    assert no_f5["top30_symmetric_difference"] == published_lofo["top30_churn"]
    # A forbidden-mutation witness: absent source data cannot be changed to a
    # measured neutral reading. This synthetic alteration is not a policy proposal.
    bad = [dict(r) for r in members]
    for row in bad:
        if row[MEMBER] is None:
            row[MEMBER] = "neutral"
    bad_admission = f.admit_members([("live", r) for r in bad])
    bad_plane = f.aggregate(bad, bad_admission.admitted)
    assert MEMBER in bad_admission.admitted
    mutation = comparison(rows, plane.scores, bad_plane.scores)
    assert mutation["rows_with_changed_raw_score"] > 0
    assert mutation["rows_moved"] > 0
    archived_gex = next(x for x in archived["rows"] if x["member"] == MEMBER)
    archive_n = archived["session"]["n_v3_buy_rows"]
    assert archive_n != len(rows)
    return {
        "schema": "options.research.gex_run_audit.v1",
        "scope": "One published artifact and its fixed buy pool; fit-free arithmetic replay only",
        "source": board["source"],
        "source_module_git_blob": SOURCE_BLOB,
        "input_extract_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "as_of": board["as_of"], "emit": board["emit"], "rows": len(rows),
        "verification": {"published_scores_match": True, "published_ranks_match": True,
            "all_member_percentiles_match": True, "all_family_display_contributions_match": True,
            "admission_receipt_matches": True, "duplicate_collapse_receipt_matches": True,
            "whole_family_LOFO_matches_published": True},
        "gex_member": {"nonnull":len(nonnull), "missing":len(values)-len(nonnull),
            "coverage":len(nonnull)/len(values), "distinct_oriented_values":len(set(nonnull)),
            "raw_verdict_counts":dict(sorted(raw_counts.items())),
            "presence_floor":f.PRESENCE_FLOOR, "minimum_nonnull_for_this_pool":math.ceil(f.PRESENCE_FLOOR*len(rows)),
            "admitted":False, "reason":"below_presence_floor", "zero_filled":False},
        "admission":plane.admission.as_dict(), "families":plane.families_present,
        "members_collapsed":plane.members_collapsed,
        "remove_gex_member_fixed_pool":no_gex,
        "remove_entire_f5_family_fixed_pool":no_f5,
        "forbidden_missing_to_neutral_mutation":{
            "synthetic_only":True,"gex_admitted_after_invalid_replacement":True, **mutation},
        "same_date_archived_observation":{
            "source":archived["source"], "coverage_blob":archived["git_blob_sha"],
            "rows":archive_n, "gex_coverage":archived_gex["coverage"],
            "gex_status":archived_gex["status"],
            "observation_fingerprint":archived["session"]["observation_fingerprint"],
            "same_as_latest_board":False,
            "join_by_date_alone_permitted":False},
        "claim_limits":["No upstream cohort/cascade source exclusion was performed.",
            "This run's zero GEX member contribution does not prove a globally options-free incumbent.",
            "Code blobs match the repository source named by the render commit; executed binary/container provenance is not attested.",
            "Source inputs, real consumer receipt, browser deployment, historical availability and predictive quality are not proved by score replay.",
            "Removing all F5 removes non-GEX evidence and is not the GEX-specific result.",
            "Same as_of dates can identify different artifact revisions and populations."]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(Path(__file__).resolve().parent)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"status":"PASS","rows":result["rows"],
        "gex_nonnull":result["gex_member"]["nonnull"],
        "gex_rank_changes":result["remove_gex_member_fixed_pool"]["rows_moved"],
        "F5_rank_changes":result["remove_entire_f5_family_fixed_pool"]["rows_moved"],
        "output_sha256":hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
