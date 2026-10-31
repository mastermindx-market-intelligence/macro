"""FIF Z0 A34: per-pack proof ledger generator.

Z0 closure-matrix row A34 requires that each of the twelve specialist packs
carries its own schema/gold/held-out/review/live proof and that no group
summary can hide a per-pack gap. This script MEASURES that state from
committed artifacts only and writes the measurement as one ledger document
(``research/financial_intelligence_fabric/FIF_A34_PACK_PROOF_LEDGER.json``):

    python3 scripts/fif_a34_pack_proof_ledger.py --out research/financial_intelligence_fabric/FIF_A34_PACK_PROOF_LEDGER.json
    python3 scripts/fif_a34_pack_proof_ledger.py --check research/financial_intelligence_fabric/FIF_A34_PACK_PROOF_LEDGER.json

Measurement rules (frozen by the A34 lane packet):

- ``schema``   present iff ``contracts/specialist_packs/pack.pkNN.v1.schema.json``
               is committed; ``catalogue_state`` is read from that contract.
- ``gold``     present only when at least one calibration label JSON exists
               under ``tests/fixtures/fundamental_forensics/pack_gold/PKNN/``.
               Producer tests are counted in ``calibration_tests`` but are NOT
               gold and never flip the state.
- ``held_out`` present only when the sealed marker exists at
               ``tests/fixtures/fundamental_forensics_held_out/packs/PKNN/labels/_SEALED``.
               Only existence is checked — this generator never reads any
               byte under the held-out root (Q0 "who may read").
- ``review``   present only with at least one PASS / PASS_WITH_NOTES row for
               the pack in ``FIF_A34_PACK_REVIEWS.json`` (rows are recorded
               verbatim; git history is never resolved).
- ``live``     present only with at least one row for the pack in
               ``FIF_A34_PACK_LIVE_PROOFS.json`` (verbatim).

The document deliberately carries no averaged, percentage or score field:
every pack's own gaps list is the summary, and ``--check`` fails when the
committed ledger is stale against a fresh generation (``generated_at``
excepted).
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent

LEDGER_REL = "research/financial_intelligence_fabric/FIF_A34_PACK_PROOF_LEDGER.json"
PROTOCOL_REL = "research/financial_intelligence_fabric/FIF_Q0_QUALITY_PROTOCOL.json"
REVIEWS_REL = "research/financial_intelligence_fabric/FIF_A34_PACK_REVIEWS.json"
LIVE_PROOFS_REL = "research/financial_intelligence_fabric/FIF_A34_PACK_LIVE_PROOFS.json"
PRODUCER_TESTS_REL = "tests/test_fif_specialist_packs.py"
CALIBRATION_GOLD_REL = "tests/fixtures/fundamental_forensics/pack_gold"
HELD_OUT_ROOT_REL = "tests/fixtures/fundamental_forensics_held_out"

LEDGER_SCHEMA = "fif.a34_pack_proof_ledger.v1"
MATRIX_ROW = "A34"
PROOF_ORDER = ("schema", "gold", "held_out", "review", "live")
REVIEW_VERDICTS_PRESENT = ("PASS", "PASS_WITH_NOTES")


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _contract_rel(pack_id: str) -> str:
    return f"contracts/specialist_packs/pack.{pack_id.lower()}.v1.schema.json"


def _calibration_test_count(root: Path, pack_id: str) -> int:
    source = (root / PRODUCER_TESTS_REL).read_text(encoding="utf-8")
    pattern = re.compile(rf"^def test_{re.escape(pack_id.lower())}(?!\d)", re.M)
    return len(pattern.findall(source))


def _calibration_label_paths(root: Path, pack_id: str) -> list[str]:
    gold_dir = root / CALIBRATION_GOLD_REL / pack_id
    if not gold_dir.is_dir():
        return []
    files = [path for path in gold_dir.rglob("*.json") if path.is_file()]
    return sorted(str(path.relative_to(root)) for path in files)


def _rows_for(rows: list[dict], pack_id: str, verdicts: tuple[str, ...] | None) -> list[dict]:
    matching = []
    for row in rows:
        if row.get("pack_id") != pack_id:
            continue
        if verdicts is not None and row.get("verdict") not in verdicts:
            continue
        matching.append(dict(row))
    return matching


def _pack_entry(root: Path, q0_pack: dict, reviews: list[dict], live_proofs: list[dict]) -> dict:
    pack_id = q0_pack["pack_id"]
    contract_path = root / _contract_rel(pack_id)
    schema_state = "present" if contract_path.is_file() else "missing"
    catalogue_state = None
    if schema_state == "present":
        catalogue_state = _read_json(contract_path).get("catalogue_state")

    label_paths = _calibration_label_paths(root, pack_id)
    calibration_labels = len(label_paths)
    gold_state = "present" if calibration_labels >= 1 else "missing"

    sealed_marker = root / HELD_OUT_ROOT_REL / "packs" / pack_id / "labels" / "_SEALED"
    sealed = os.path.exists(sealed_marker)
    held_out_state = "present" if sealed else "missing"

    review_rows = _rows_for(reviews, pack_id, REVIEW_VERDICTS_PRESENT)
    live_rows = _rows_for(live_proofs, pack_id, None)

    proofs = {
        "schema": {
            "state": schema_state,
            "evidence": [_contract_rel(pack_id)] if schema_state == "present" else [],
            "catalogue_state": catalogue_state,
        },
        "gold": {
            "state": gold_state,
            "evidence": label_paths,
            "calibration_tests": _calibration_test_count(root, pack_id),
            "calibration_labels": calibration_labels,
        },
        "held_out": {
            "state": held_out_state,
            "sealed": sealed,
            "quality_label": None,
        },
        "review": {
            "state": "present" if review_rows else "missing",
            "evidence": review_rows,
        },
        "live": {
            "state": "present" if live_rows else "missing",
            "evidence": live_rows,
        },
    }
    gaps = [proof for proof in PROOF_ORDER if proofs[proof]["state"] == "missing"]
    return {"pack_id": pack_id, "name": q0_pack["name"], "proofs": proofs, "gaps": gaps}


def build_ledger(root: Path = ROOT) -> dict:
    """Regenerate the A34 ledger document from committed artifacts."""
    protocol = _read_json(root / PROTOCOL_REL)
    reviews_path = root / REVIEWS_REL
    live_proofs_path = root / LIVE_PROOFS_REL
    reviews = _read_json(reviews_path).get("reviews", []) if reviews_path.is_file() else []
    live_proofs = _read_json(live_proofs_path).get("proofs", []) if live_proofs_path.is_file() else []

    packs = [
        _pack_entry(root, q0_pack, reviews, live_proofs)
        for q0_pack in protocol["packs"]
    ]
    packs_with_gaps = sum(1 for pack in packs if pack["gaps"])
    return {
        "schema": LEDGER_SCHEMA,
        "matrix_row": MATRIX_ROW,
        "base_commit": _git_head(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_id": protocol["protocol_id"],
        "packs": packs,
        "gaps_by_pack": {pack["pack_id"]: pack["gaps"] for pack in packs},
        "packs_with_gaps": packs_with_gaps,
        "packs_complete": len(packs) - packs_with_gaps,
    }


def _first_diffs(committed: dict, fresh: dict) -> list[str]:
    diffs = []
    for key in sorted(set(committed) | set(fresh)):
        if committed.get(key) != fresh.get(key):
            diffs.append(key)
    return diffs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out", metavar="PATH", help="write a fresh ledger to PATH")
    mode.add_argument("--check", metavar="PATH", help="compare the committed ledger at PATH to a fresh generation")
    args = parser.parse_args(argv)

    if args.out:
        document = build_ledger()
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(
            f"FIF A34 ledger written: {len(document['packs'])} packs, "
            f"packs_with_gaps={document['packs_with_gaps']} -> {out_path}"
        )
        return 0

    check_path = Path(args.check)
    committed = _read_json(check_path)
    fresh = build_ledger()
    # ``generated_at`` is a wall clock and ``base_commit`` is the HEAD the
    # ledger was built at, which a committed ledger can never equal (the
    # commit that carries it is created after it is written); neither is a
    # proof, so neither takes part in the staleness comparison (review F1).
    volatile = ("generated_at", "base_commit")
    committed_without_time = {key: value for key, value in committed.items() if key not in volatile}
    fresh_without_time = {key: value for key, value in fresh.items() if key not in volatile}
    if committed_without_time != fresh_without_time:
        diffs = _first_diffs(committed_without_time, fresh_without_time)
        print(f"FIF A34 ledger STALE at {check_path}; differing sections: {', '.join(diffs)}")
        print("Regenerate: python3 scripts/fif_a34_pack_proof_ledger.py --out " + str(check_path))
        return 1
    print(f"FIF A34 ledger fresh: {len(fresh['packs'])} packs, packs_with_gaps={fresh['packs_with_gaps']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
