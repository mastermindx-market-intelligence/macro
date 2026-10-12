#!/usr/bin/env python3
"""build_seal.py — C1: the outcome-free seal builder for the S1 residual lane.

Writes, BEFORE any outcome exists (SL §5):
  runs/s1_residual/SEAL_AND_BUDGET.json / .md
  runs/s1_residual/PREREG_SPEC.json        (prereg_digest_sha256 recorded in the seal)
  runs/s1_residual/INPUT_MANIFEST.json     (path -> blob for every input)
  runs/s1_residual/manifests/*.jsonl       (membership, canonical JSONL per (protocol, subject, h))
  runs/s1_residual/CHALLENGER_UNIVERSE.json

The builder reads ONLY market calendars and index dates (plus identity metadata
from security_master, which is not price/volume data and is disclosed here). A
spy wraps the store and the audit result is embedded in the seal: if any
non-index access is attempted, the build fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from lib import nyse_calendar  # noqa: E402
from s1_challenger import UNIVERSE_END, UNIVERSE_START, build_universe  # noqa: E402
from s1_data import GitBlobStore, IndexOnlySpy  # noqa: E402
from s1_manifest import (build_rows, canonical_line, manifest_bytes,  # noqa: E402
                         split_digests)
from s1_prereg import (BASE, BRANCH, BENCHES, D1_LABELS, ENGINE_CITATIONS,  # noqa: E402
                       AUTHORITY_FLAGS, HORIZONS, INPUT_PINS, LANE, RUNS_REL,
                       S0_BLOBS, SUBJECTS, VERSION, build_spec, canonical_json,
                       prereg_digest)

SECURITY_MASTER = "data/reference/security_master.parquet"
SECURITY_IDS = ["SEC:US-XNYS-BABA", "SEC:HK-XHKG-09988", "SEC:HK-XHKG-00700"]

# (protocol, subject counter) layout: P03 reuses the P01/P02 subjects.
PROTOCOL_SUBJECTS = {
    "P01": SUBJECTS["P01"],
    "P02": SUBJECTS["P02"],
    "P03": SUBJECTS["P01"] + SUBJECTS["P02"],
}


def identity_facts(store: GitBlobStore) -> dict:
    """Identity metadata ONLY (security_id, issuer_id, state, ingested_at).

    Disclosed: this is a retrospective join over existing Data OS ids (A07);
    nothing is derived from a ticker, name or CIK.
    """
    cols = store.read_columns(SECURITY_MASTER, ["security_id", "issuer_id",
                                                "issuer_state", "ingested_at"])
    out = {}
    for sid, issuer, state, ingested in zip(cols["security_id"], cols["issuer_id"],
                                            cols["issuer_state"], cols["ingested_at"]):
        if sid in SECURITY_IDS:
            out[sid] = {
                "canonical_issuer_id": issuer if isinstance(issuer, str) and issuer
                else "UNRESOLVED",
                "identity_state": state,
                "ingested_at": str(ingested),
            }
    for sid in SECURITY_IDS:
        if sid not in out:
            raise RuntimeError(f"security_master has no row for {sid}")
    return out


def build_all(repo_root: Path, input_ref: str, out_dir: Path) -> dict:
    store = GitBlobStore(repo_root, input_ref, dict(INPUT_PINS))
    store.verify_all()

    spy = IndexOnlySpy(store)

    # -- identity metadata (not price/volume; read_columns, disclosed) ------- #
    ident = identity_facts(store)

    # -- manifests: outcome-free, index dates only --------------------------- #
    manifests: dict[str, dict] = {}
    membership_rows = []
    for pid in ("P01", "P02", "P03"):
        for subj in PROTOCOL_SUBJECTS[pid]:
            dates = spy.index_dates(subj["data_path"])
            last_bar = dates[-1]
            for h in HORIZONS:
                rows = build_rows(pid, subj["issuer_key"], subj["counter"],
                                  subj["security_id"], subj["market"], h, dates, last_bar)
                name = f"{pid}_{subj['counter']}_{h}.jsonl"
                digests = split_digests(rows)
                manifests[name] = {"bytes": manifest_bytes(rows), "digests": digests,
                                   "rows": rows}
                for sp, info in digests.items():
                    membership_rows.append({
                        "protocol_id": pid, "version": VERSION,
                        "subject": subj["counter"], "security_id": subj["security_id"],
                        "h": h, "split": sp, "count": info["count"],
                        "membership_sha256": info["membership_sha256"],
                    })

    # -- challenger universe: outcome-free, schemas + index dates only ------- #
    sessions = nyse_calendar.sessions_between(UNIVERSE_START, UNIVERSE_END)
    universe = build_universe(spy, lambda p: store.rev_parse_ref_path(p), sessions)

    audit = {
        "spy_calls": sorted(set(spy.calls)),
        "index_only": set(spy.calls) <= {"schema", "index_dates", "list_dir"},
        "note": "the seal builder requested no price/volume column: the spy surface is "
                "index dates, schemas and directory listings only; identity metadata came "
                "from one read_columns call on security_master (disclosed above)",
    }
    if not audit["index_only"]:
        raise RuntimeError(f"SEAL BUILD FAIL-CLOSED: non-index access {audit['spy_calls']}")

    spec = build_spec()
    digest = prereg_digest(spec)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifests").mkdir(exist_ok=True)

    input_manifest = {
        "input_ref": input_ref,
        "pins": dict(store.pins),
        "s0_docs": {k: {"path": p, "blob": b} for k, (p, b) in S0_BLOBS.items()},
        "engine": {k: dict(v) for k, v in ENGINE_CITATIONS.items()},
        "challenger_universe_ref": "CHALLENGER_UNIVERSE.json (admitted paths carry their "
                                   "own blob ids)",
        "identity_source": {"path": SECURITY_MASTER,
                            "blob": store.pins[SECURITY_MASTER],
                            "fields": ["security_id", "issuer_id", "issuer_state",
                                       "ingested_at"],
                            "kind": "identity metadata, never price/volume"},
    }

    seal = {
        "lane": LANE,
        "version": VERSION,
        "base": BASE,
        "branch": BRANCH,
        "input_ref": input_ref,
        "labels": D1_LABELS,
        "authority_flags": AUTHORITY_FLAGS,
        "families": {
            "P01": {"family": "sni.s1_residual.P01", "declared_budget": 6,
                    "itemized_count": 6, "reg_s8_canonical": "sni.s0.P01"},
            "P02": {"family": "sni.s1_residual.P02", "declared_budget": 4,
                    "itemized_count": 12, "reg_s8_canonical": "sni.s0.P02"},
            "P03": {"family": "sni.s1_residual.P03", "declared_budget": 4,
                    "itemized_count": 21, "reg_s8_canonical": "sni.s0.P03"},
        },
        "trial_ledger_path": f"{RUNS_REL}/trial_ledger.jsonl",
        "membership_table": sorted(membership_rows,
                                   key=lambda r: (r["protocol_id"], r["subject"], r["h"],
                                                  r["split"])),
        "s0_blob_ids": {k: {"path": p, "blob": b} for k, (p, b) in S0_BLOBS.items()},
        "prereg_digest_sha256": digest,
        "identity": ident,
        "seal_builder_audit": audit,
        "outcome_free": True,
    }

    write_json(out_dir / "PREREG_SPEC.json", spec)
    write_json(out_dir / "INPUT_MANIFEST.json", input_manifest)
    write_json(out_dir / "CHALLENGER_UNIVERSE.json", universe)
    for name, m in sorted(manifests.items()):
        (out_dir / "manifests" / name).write_bytes(m["bytes"])
    write_json(out_dir / "SEAL_AND_BUDGET.json", seal)
    (out_dir / "SEAL_AND_BUDGET.md").write_text(render_seal_md(seal, manifests, universe),
                                                encoding="utf-8")
    return {"seal": seal, "manifests": manifests, "universe": universe, "spec": spec,
            "digest": digest}


def write_json(path: Path, obj: dict) -> None:
    path.write_text(canonical_json(obj) + "\n", encoding="utf-8")


def render_seal_md(seal: dict, manifests: dict, universe: dict) -> str:
    L = ["# SEAL_AND_BUDGET — sni s1_residual v1", "",
         "HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met. Sealed BEFORE any "
         "outcome. Authority flags all false.", ""]
    L.append(f"- lane: {seal['lane']} v{seal['version']}")
    L.append(f"- BASE: {seal['base']}")
    L.append(f"- branch: {seal['branch']}")
    L.append(f"- input_ref: {seal['input_ref']}")
    L.append(f"- prereg_digest_sha256: {seal['prereg_digest_sha256']}")
    L.append(f"- trial_ledger_path: {seal['trial_ledger_path']}")
    L.append("")
    L.append("## Labels (D1)")
    for lab in seal["labels"]:
        L.append(f"- {lab}")
    L.append("")
    L.append("## Families, budgets, itemized grids, REG §8 mapping")
    L.append("")
    L.append("| protocol | family | declared budget (floor) | itemized grid | REG §8 canonical |")
    L.append("|---|---|---|---|---|")
    for pid, f in seal["families"].items():
        L.append(f"| {pid} | {f['family']} | {f['declared_budget']} | "
                 f"{f['itemized_count']} | {f['reg_s8_canonical']} |")
    L.append("")
    L.append("Itemized grids: P01 2 baselines x 3 h = 6; P02 2 subjects x 2 baselines x "
             "3 h = 12; P03 6 BABA cohort + 3 challenger + 12 HK-descriptive = 21.")
    L.append("")
    L.append("## Membership table (protocol, subject, h, split)")
    L.append("")
    L.append("| protocol | subject | h | split | count | membership_sha256 |")
    L.append("|---|---|---|---|---|---|")
    for r in seal["membership_table"]:
        L.append(f"| {r['protocol_id']} | {r['subject']} | {r['h']} | {r['split']} | "
                 f"{r['count']} | {r['membership_sha256']} |")
    L.append("")
    L.append("## Manifest files")
    L.append("")
    for name in sorted(manifests):
        total = sum(i["count"] for i in manifests[name]["digests"].values())
        L.append(f"- `manifests/{name}`: {total} rows")
    L.append("")
    L.append("## Challenger universe (outcome-free census)")
    L.append("")
    L.append(f"- files examined: {universe['files_examined']}")
    L.append(f"- admitted: {universe['admitted_count']}")
    L.append(f"- rejected by reason: {json.dumps(universe['rejected_by_reason'], sort_keys=True)}")
    L.append("")
    L.append("## Line-number drift noted (S0 never edited)")
    L.append("")
    L.append("- S0 cites trial_ledger L48/L126/L159/L210/L214/L242; at BASE the same "
             "symbols sit at L49/L146/L202/L253/L257/L287.")
    L.append("- Sidedness GAP recorded: REG did not fix H0_2 sidedness; frozen two-sided "
             "at this seal (D6).")
    L.append("- REG §6 seal table stays empty here; the seat integrates the lane seal "
             "into REG §6.")
    L.append("- D4 interpretation note: manifests carry one row per (protocol, subject, h); "
             "the retirement ledger row cites one membership_sha256 assembled from the "
             "affected per-h digests (see run_s1).")
    L.append("")
    L.append("## Outcome-free audit")
    L.append("")
    L.append(f"- spy calls: {sorted(set(seal['seal_builder_audit']['spy_calls']))}")
    L.append("- index_only: true (fail-closed otherwise)")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-ref", required=True)
    ap.add_argument("--repo-root", default=str(Path.cwd()))
    ap.add_argument("--out-dir", default=RUNS_REL)
    a = ap.parse_args()
    res = build_all(Path(a.repo_root), a.input_ref, Path(a.out_dir))
    n_members = len(res["seal"]["membership_table"])
    print(f"seal written to {a.out_dir}: prereg digest {res['digest'][:12]}…, "
          f"{len(res['manifests'])} manifests, {n_members} membership rows, "
          f"challenger universe {res['universe']['admitted_count']} admitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
