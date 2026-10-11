"""S2 seal builder — C1. Outcome-free by construction.

Builds every seal artifact BEFORE any outcome exists:
  SEAL_AND_BUDGET.json / SEAL_AND_BUDGET.md, PREREG_SPEC.json (with
  prereg_digest_sha256), INPUT_MANIFEST.json, EVENT_CENSUS.json,
  E_COVERAGE_CENSUS.json and manifests/<Pxx>_h<h>.jsonl.

All state comes from s2_state.compute_state (metadata only: profiles, coverage
reports, events/earnings metadata columns, id columns, calendar arithmetic).
No price or volume column is ever requested; no return is ever resolved.

Usage:
  python3 build_seal.py --input-ref <BASE sha> --out-dir <runs/s2_event_response>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from s2_loaders import GitBlobLoader, verify_pinned_blobs  # noqa: E402
from s2_selection import coverage_census_rows  # noqa: E402
from s2_seal import (AUTHORITY_FLAGS, BASE_COMMIT, BRANCH, GRADE_HORIZONS,
                     GRADED_ISSUER, GRADED_LEG_LABEL, IDENTITY_VIEW,
                     INPUT_MANIFEST, LABEL_HISTORICAL, LANE, NOT_SUPPORTED_LINE,
                     NOT_SUPPORTED_PROTOCOLS, PROTOCOL_TITLE, PROTOCOLS,
                     REG_CANONICAL_FAMILY, S0_BLOB_IDS, TRIAL_LEDGER_REL_PATH,
                     build_prereg_spec, prereg_digest)  # noqa: E402
from s2_state import PROTOCOL_FAMILY, compute_state  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-ref", default=BASE_COMMIT)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repo-root", default=None)
    args = ap.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else None
    if repo_root is None:
        from s2_loaders import _git
        repo_root = Path(_git(".", "rev-parse", "--show-toplevel"))
    out = Path(args.out_dir)
    (out / "manifests").mkdir(parents=True, exist_ok=True)

    loader = GitBlobLoader(repo_root, args.input_ref)
    verify_pinned_blobs(repo_root, args.input_ref)
    state = compute_state(loader)
    collapse = state["collapse"]

    # -- manifests + membership table --------------------------------------- #
    membership_rows: list[dict] = []
    for pid in PROTOCOLS:
        mem = state["membership"][pid]
        for h in GRADE_HORIZONS:
            (out / "manifests" / f"{pid}_h{h}.jsonl").write_text(
                "".join(mem["lines_by_h"].get(h, [])), encoding="utf-8")
        membership_rows.extend(mem["table_rows"])

    # -- prereg spec + digest ----------------------------------------------- #
    from run_s2 import full_spec_digest  # single spec construction, no drift
    spec, digest = full_spec_digest(state)

    # -- seal artifacts ------------------------------------------------------ #
    seal = {
        "lane": LANE,
        "base_commit": BASE_COMMIT,
        "input_ref": args.input_ref,
        "branch": BRANCH,
        "version": "v1",
        "labels": {"status": LABEL_HISTORICAL,
                   "identity_view": IDENTITY_VIEW,
                   "authority_flags": dict(AUTHORITY_FLAGS)},
        "families": [
            {"protocol_id": pid,
             "title": PROTOCOL_TITLE[pid],
             "family": PROTOCOL_FAMILY[pid],
             "counting_clock": "MARKET_US",
             "ledger_family": f"sni.s2_event_response.{pid}",
             "reg_canonical_family": REG_CANONICAL_FAMILY[pid],
             "declared_budget": 6,
             "itemized_grid_size": 12,
             "reg_note": "REG §6 stays empty in S2; the seat integrates the seal row"}
            for pid in PROTOCOLS
        ],
        "not_supported_in_s2": [{"protocol_id": p, "line": NOT_SUPPORTED_LINE}
                                for p in NOT_SUPPORTED_PROTOCOLS],
        "graded_cohort": {
            "issuer_group": GRADED_ISSUER,
            "graded_leg": GRADED_LEG_LABEL[GRADED_ISSUER],
            "census_only": [
                "tencent issuer group (00700) — counted, listed, abstained, never graded",
                "HK legs (9988, 0700) — never graded (V0 row 14)"],
        },
        "trial_ledger_path": TRIAL_LEDGER_REL_PATH,
        "s0_blob_ids": {k: dict(v) for k, v in S0_BLOB_IDS.items()},
        "input_manifest": dict(INPUT_MANIFEST),
        "membership_table": membership_rows,
        "prereg_digest_sha256": digest,
        "census_counts": {
            "event_rows": len(state["event_rows"]),
            "earnings_rows": len(state["earning_rows"]),
            "selected": len(state["selected"]),
            "programmes": state["programmes"],
        },
        "collapse_counts": collapse["counts"],
    }
    (out / "SEAL_AND_BUDGET.json").write_text(
        json.dumps(seal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "PREREG_SPEC.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "INPUT_MANIFEST.json").write_text(
        json.dumps({k: {"blob": v, "input_ref": args.input_ref}
                    for k, v in sorted(INPUT_MANIFEST.items())},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "EVENT_CENSUS.json").write_text(
        json.dumps({"label": LABEL_HISTORICAL,
                    "rows": sorted(state["census_rows"],
                                   key=lambda r: (r["issuer_key"], r["id"]))},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cov_rows = coverage_census_rows(state["coverage_reports"])
    (out / "E_COVERAGE_CENSUS.json").write_text(
        json.dumps({"label": LABEL_HISTORICAL,
                    "cells": cov_rows,
                    "counts": {iss: dict(sorted(Counter(
                        c["state"] for c in cov_rows
                        if c["issuer_key"] == iss).items()))
                        for iss in ("alibaba", "tencent")}},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "SEAL_AND_BUDGET.md").write_text(render_seal_md(seal, collapse),
                                            encoding="utf-8")
    print(f"seal written to {out}")
    print(f"prereg_digest_sha256 = {digest}")
    print(f"census rows = {len(state['census_rows'])}; "
          f"selected = {len(state['selected'])}; "
          f"programmes = {[p['member_ids'] for p in state['programmes']]}")
    print(f"events of record = {collapse['counts']['events_after_step2_and_step3']}")
    return 0


def render_seal_md(seal: dict, collapse: dict) -> str:
    lines = []
    a = lines.append
    a("# S2 SEAL_AND_BUDGET — P04–P06 frozen before any outcome")
    a("")
    a(f"Lane `{seal['lane']}` v{seal['version']}; BASE `{seal['base_commit']}`; "
      f"branch `{seal['branch']}`; input_ref `{seal['input_ref']}`.")
    a("")
    a(f"**Label.** {LABEL_HISTORICAL}")
    a("")
    a(f"**Authority flags.** {json.dumps(AUTHORITY_FLAGS, sort_keys=True)} — all false.")
    a("")
    a("## Families, budgets, itemized grids, REG mapping")
    a("")
    a("| protocol | family | ledger family (S2) | REG canonical family (R1 step) | declared budget | itemized |")
    a("|---|---|---|---|---|---|")
    for f in seal["families"]:
        a(f"| {f['protocol_id']} | {f['family']} | {f['ledger_family']} | "
          f"{f['reg_canonical_family']} | {f['declared_budget']} (FLOOR) | "
          f"{f['itemized_grid_size']} |")
    a("")
    a("Itemized grid per family: 3 frozen baselines x 3 horizons = 9 configs, "
      "plus the challenger column x 3 horizons = 3 (logged even when NOT "
      "ESTIMABLE) = 12. Budgets are floors, never caps (REG §8 L205). No "
      "`sni.s0.*` ledger row is ever written from S2; the mapping is recorded "
      "here for the later R1 step only.")
    a("")
    a("## Not supported in S2")
    a("")
    for row in seal["not_supported_in_s2"]:
        a(f"- {row['protocol_id']}: {row['line']}")
    a("")
    a("## Graded cohort")
    a("")
    a(f"- Graded issuer group: **{seal['graded_cohort']['issuer_group']}** on "
      f"{seal['graded_cohort']['graded_leg']}.")
    for c in seal["graded_cohort"]["census_only"]:
        a(f"- CENSUS-ONLY: {c}.")
    a("")
    a("## Membership table (protocol, h, split, count, membership_sha256)")
    a("")
    a("| protocol | h | split | count | membership_sha256 |")
    a("|---|---|---|---|---|")
    for r in seal["membership_table"]:
        sha = r["membership_sha256"] or ""
        a(f"| {r['protocol_id']} | {r['horizon']} | {r['split']} | "
          f"{r['count']} | {sha} |")
    a("")
    a("## Collapse receipts (metadata only)")
    a("")
    a(f"- literal row count pre step 0: {collapse['counts']['literal_row_count_pre_step0']}")
    a(f"- kept after step 0: {collapse['counts']['kept_after_step0']}")
    a(f"- events after step 2: {collapse['counts']['events_after_step2']}")
    a(f"- events of record after step 3: {collapse['counts']['events_after_step2_and_step3']}")
    for e in collapse["counts"]["excluded_and_listed"]:
        a(f"- excluded-and-listed [{e['step']}] {e['id']} ({e['issuer_key']}): "
          f"{e['reason']}")
    a("")
    a("## DEVIATIONS and S0-difference log")
    a("")
    a("- Tencent counter local_code: the packet's prose examples say `0700`; the "
      "profile's `hkd_0700.local_code` is `00700` (tencent.yml). The exact-token "
      "rule is applied against the profile local_code; the packet's own anchors "
      "(news_id 12280990; false positive 12291963, token `40700`) reproduce "
      "exactly under it.")
    a("- Line drift: S0 cites trial_ledger L48/L126/L159/L210/L214/L242/L296 and "
      "grading_stats L56/L121; at BASE these sit at DEFAULT_PATH L49, log_trial "
      "L146, log_declared_budget L202, literal_n L253, effective_n L257, "
      "declared_budget L287, register_trials L296, wilson_ci L56, "
      "block_bootstrap_ci L121. The APIs are identical; only line numbers "
      "drifted. S0 was not edited.")
    a("- The receipt's commit identity is carried by `input_ref` + the pinned "
      "INPUT_MANIFEST blob ids (content-derived, byte-stable); the branch head "
      "at run time is never stamped, so `--check` byte-compares stay stable. "
      "The seal commit itself is named by the seat when it integrates the REG §6 "
      "row, which stays empty in S2.")
    a("- Census-only episodes (tencent) carry split labels and appear in the "
      "membership manifests with graded_leg NONE — census only (V0 row 14); "
      "they never enter any graded honest-N.")
    a("- The near-token probe also matches a counter code's unpadded key form "
      "(e.g. `0700` for `00700`) so the packet's false-positive class "
      "(token `40700`) stays visibly listed.")
    a("")
    a("## Receipts")
    a("")
    a(f"- prereg_digest_sha256: `{seal['prereg_digest_sha256']}`")
    a(f"- S0 blob ids: REG `{S0_BLOB_IDS['REG']['blob']}`, IL "
      f"`{S0_BLOB_IDS['IL']['blob']}`, SL `{S0_BLOB_IDS['SL']['blob']}`")
    a(f"- trial ledger path: `{TRIAL_LEDGER_REL_PATH}` (written at evidence time, "
      "never by this builder)")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
