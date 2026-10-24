#!/usr/bin/env python3
"""GMI ORCH-REL M2 judge CLI: pack, status, verify, materialize.

``pack``        turns harvested candidates into judge packs + the frozen guide;
``status``      prints per-pack judged/missing counts;
``verify``      validates judgments and dry-runs every K3-K9 mapping (cache-only);
``materialize`` writes extraction rows, source excerpts and the judging ledger.

No network anywhere: EDGAR bytes come only from the integrity-checked cache.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import harvest as rel_harvest  # noqa: E402
from engine.company_intelligence.relationships import judge as rel_judge  # noqa: E402

DEFAULT_INPUTS = "research/theme_graph/gmi_relationships_20261021/m2_inputs"
DEFAULT_MANIFEST = "research/theme_graph/coverage_20261019/UNIVERSE_MANIFEST.json"
LEAVES = ("P", "D1a", "D1b", "D2a", "D2b")


def _default_cache_root() -> str:
    return os.environ.get("GMI_EDGAR_CACHE") or os.path.expanduser(
        "~/.cache/gmi_edgar"
    )


def _dirname(leaf: str, slice_label) -> str:
    if not slice_label:
        return leaf
    return f"{leaf}.{slice_label.replace('/', 'of')}"


def _resolve_selection(args):
    """(inputs, issuers, dirname) after pin-verified input loading (K12)."""
    inputs = rel_harvest.load_inputs(args.inputs)
    issuers = rel_harvest.leaf_issuers(inputs["leaves"], args.leaf)
    slice_label = None
    if getattr(args, "slice", None):
        i, n = (int(part) for part in args.slice.split("/", 1))
        issuers = rel_harvest.slice_issuers(issuers, i, n)
        slice_label = f"{i}/{n}"
    return inputs, issuers, _dirname(args.leaf, slice_label)


# --- pack -----------------------------------------------------------------------


def cmd_pack(args) -> int:
    _inputs, _issuers, dirname = _resolve_selection(args)
    base = Path(args.workdir) / dirname
    candidates_path = base / "candidates.jsonl"
    if not candidates_path.is_file():
        print(
            f"relationship_m2_judge: missing {candidates_path}", file=sys.stderr
        )
        return 2
    candidates_sha = hashlib.sha256(candidates_path.read_bytes()).hexdigest()
    packs_dir = base / "packs"
    index_path = packs_dir / "index.json"
    if index_path.is_file():
        existing = json.loads(index_path.read_bytes().decode("utf-8"))
        if existing.get("candidates_sha256") != candidates_sha:
            print(
                "relationship_m2_judge: packs/ holds a different "
                "candidates_sha256; delete packs/ or re-run the harvester "
                "(rc 2)",
                file=sys.stderr,
            )
            return 2
    candidates = rel_judge.read_jsonl(candidates_path)
    packs, index = rel_judge.build_packs(
        candidates, args.leaf, dirname, per_pack=args.per_pack
    )
    packs_dir.mkdir(parents=True, exist_ok=True)
    (packs_dir / "GUIDE.md").write_bytes(
        (rel_judge.JUDGING_GUIDE + "\n").encode("utf-8")
    )
    index["candidates_sha256"] = candidates_sha
    for pack in packs:
        name = f"pack_{pack['pack']:03d}.json"
        (packs_dir / name).write_bytes(rel_judge.canonical_json_bytes(pack))
    index_path.write_bytes(rel_judge.canonical_json_bytes(index))
    print(
        f"relationship_m2_judge: packed leaf={args.leaf} dirname={dirname} "
        f"candidates={len(candidates)} packs={len(packs)} per_pack={args.per_pack}"
    )
    return 0


# --- status ---------------------------------------------------------------------


def cmd_status(args) -> int:
    _inputs, _issuers, dirname = _resolve_selection(args)
    base = Path(args.workdir) / dirname
    index_path = base / "packs" / "index.json"
    if not index_path.is_file():
        print(f"relationship_m2_judge: missing {index_path}", file=sys.stderr)
        return 2
    index = json.loads(index_path.read_bytes().decode("utf-8"))
    all_ids = {
        cid for entry in index["packs"] for cid in entry["candidate_ids"]
    }
    judged = set()
    judgments_dir = base / (index.get("judgments_dir") or "judgments")
    if judgments_dir.is_dir():
        judged = {
            record.get("candidate_id")
            for record in rel_judge.read_judgments(judgments_dir, [])[1]
        }
    for entry in index["packs"]:
        total = len(entry["candidate_ids"])
        have = sum(1 for cid in entry["candidate_ids"] if cid in judged)
        print(
            f"pack {entry['pack']:03d}: judged {have}/{total} "
            f"missing {total - have}"
        )
    print(
        f"relationship_m2_judge: status leaf={args.leaf} dirname={dirname} "
        f"judged {len(judged & all_ids)}/{len(all_ids)}"
    )
    return 0


# --- verify / materialize ---------------------------------------------------------


def _evaluate(args, *, enforce_committed: bool, allow_missing: bool):
    _inputs, _issuers, dirname = _resolve_selection(args)
    repo_root = getattr(args, "repo_root", None) or REPO_ROOT
    committed_dir = getattr(args, "committed_extraction", None)
    if committed_dir is None:
        committed_dir = (
            Path(repo_root)
            / "research/theme_graph/gmi_relationships_20261021/extraction"
        )
    return rel_judge.evaluate_materialize(
        leaf=args.leaf,
        dirname=dirname,
        workdir=args.workdir,
        repo_root=repo_root,
        committed_dir=committed_dir,
        inputs_dir=args.inputs,
        manifest_path=args.manifest,
        cache_root=args.cache_root,
        allow_missing=allow_missing,
        enforce_committed=enforce_committed,
    )


def cmd_verify(args) -> int:
    # verify is a pure K3-K9 dry-run: the committed-extraction admission rule
    # belongs to materialize, so it never suppresses a mapping here.
    rc, result = _evaluate(args, enforce_committed=False, allow_missing=True)
    if rc == 2:
        print(
            f"relationship_m2_judge: verify refused: {result.get('error')}",
            file=sys.stderr,
        )
        return 2
    codes = result["codes"]
    for code, count in codes.items():
        print(f"{code}: {count}")
    print(
        f"relationship_m2_judge: verify leaf={args.leaf} "
        f"candidates={result['candidates_total']} judged={result['judged']} "
        f"missing={result['missing']} observations={result['observations']} "
        f"assessments={result['assessments']} codes={sum(codes.values())}"
    )
    if args.strict and (codes or result["missing"]):
        return 1
    return 0


def cmd_materialize(args) -> int:
    rc, result = _evaluate(args, enforce_committed=True,
                           allow_missing=args.allow_missing)
    if rc == 2:
        print(
            f"relationship_m2_judge: materialize refused: "
            f"{result.get('error')}",
            file=sys.stderr,
        )
        return 2
    rel_judge.write_materialized(
        result, workdir=args.workdir, dirname=result["dirname"],
        repo_root=args.repo_root,
    )
    print(
        f"relationship_m2_judge: materialized leaf={result['leaf']} "
        f"dirname={result['dirname']} observations={result['observations']} "
        f"assessments={result['assessments']} coverage={len(result['coverage'])} "
        f"edges={len(result['edges'])} codes={sum(result['codes'].values())}"
    )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(sub_parser):
        sub_parser.add_argument(
            "--leaf", required=True, choices=list(LEAVES)
        )
        sub_parser.add_argument("--workdir", required=True)
        sub_parser.add_argument(
            "--slice", default=None, help="i/n — dirname becomes <leaf>.iofn"
        )
        sub_parser.add_argument("--inputs", default=DEFAULT_INPUTS)

    pack_parser = sub.add_parser("pack", help="build judge packs + guide")
    common(pack_parser)
    pack_parser.add_argument(
        "--per-pack", type=int, default=rel_judge.PER_PACK_DEFAULT
    )

    status_parser = sub.add_parser("status", help="per-pack judged counts")
    common(status_parser)

    verify_parser = sub.add_parser(
        "verify", help="validate judgments + dry-run every K3-K9 mapping"
    )
    common(verify_parser)
    verify_parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    verify_parser.add_argument("--repo-root", default=str(REPO_ROOT))
    verify_parser.add_argument("--cache-root", default=_default_cache_root())
    verify_parser.add_argument(
        "--strict", action="store_true",
        help="exit 1 when any refusal or missing judgment exists",
    )

    materialize_parser = sub.add_parser(
        "materialize", help="write extraction rows, sources and the ledger"
    )
    common(materialize_parser)
    materialize_parser.add_argument(
        "--repo-root", default=str(REPO_ROOT),
        help="output root (defaults to the repo; candidates are never written)",
    )
    materialize_parser.add_argument(
        "--committed-extraction", default=None,
        help="directory of committed extraction *.jsonl whose issuers are "
             "skipped whole (default: the repo's extraction dir)",
    )
    materialize_parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    materialize_parser.add_argument(
        "--cache-root", default=_default_cache_root()
    )
    materialize_parser.add_argument(
        "--allow-missing", action="store_true",
        help="proceed when judgments are missing (outcome missing, rc 0)",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "pack":
            return cmd_pack(args)
        if args.command == "status":
            return cmd_status(args)
        if args.command == "verify":
            return cmd_verify(args)
        return cmd_materialize(args)
    except rel_harvest.InputPinMismatch as error:
        print(
            f"relationship_m2_judge: input pin mismatch: {error}",
            file=sys.stderr,
        )
        return 2
    except ValueError as error:
        print(f"relationship_m2_judge: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
