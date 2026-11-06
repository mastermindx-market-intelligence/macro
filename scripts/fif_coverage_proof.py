#!/usr/bin/env python3
"""FIF C2 coverage proof CLI (acceptance case A36, masterplan node V1).

Reads a frozen thresholds config, the governed metric catalog, and a
``fundamental_forensics.coverage_manifest/v1`` document, computes the pure
coverage proof from ``engine/fundamental_forensics/coverage_proof.py``, and
emits one JSON report on stdout (or ``--out``) plus the fixed print block on
stderr when ``--print`` is given.

Exit codes:
  * 0 — the proof was computed, whether or not the targets are met;
  * 2 — an input refusal (a ``CoverageProofError``, or a naive or unparseable
    ``--proved-at``);
  * 4 — ``--require-acceptance`` was given and the report is not
    acceptance-eligible.

No network.  The only write is the ``--out`` file.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.fundamental_forensics.coverage_proof import (  # noqa: E402
    CoverageProofError,
    load_manifest,
    load_metric_sets,
    load_thresholds,
    prove_coverage,
    render_print,
)

DEFAULT_CATALOG = REPO_ROOT / "config" / "fundamental_forensics" / "metrics" / "v1" / "metric_catalog.yaml"
DEFAULT_FORMULAS = REPO_ROOT / "config" / "fundamental_forensics" / "metrics" / "v1" / "formulas" / "core.yaml"


def _parse_proved_at(raw: str) -> datetime | None:
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _run_prove(args: argparse.Namespace) -> int:
    thresholds = load_thresholds(args.thresholds)
    direct_ids, formula_ids = load_metric_sets(
        args.catalog, args.formulas, thresholds
    )
    manifest_bytes = load_manifest(args.manifest)
    proved_at = _parse_proved_at(args.proved_at)
    if proved_at is None:
        print(
            f"refused: --proved-at is not a parseable ISO timestamp: {args.proved_at!r}",
            file=sys.stderr,
        )
        return 2
    report = prove_coverage(
        manifest_bytes,
        thresholds,
        direct_ids,
        formula_ids,
        proved_at=proved_at,
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    if args.print_block:
        sys.stderr.write(render_print(report))
    if args.require_acceptance and not report["acceptance_eligible"]:
        return 4
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fif_coverage_proof.py",
        description="Prove frozen C2 coverage tiers from a coverage manifest.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prove = subparsers.add_parser("prove", help="compute one coverage proof")
    prove.add_argument("--manifest", required=True, help="coverage manifest JSON path")
    prove.add_argument("--thresholds", required=True, help="frozen thresholds JSON path")
    prove.add_argument(
        "--proved-at",
        required=True,
        dest="proved_at",
        help="timezone-aware ISO timestamp echoed as the proof clock",
    )
    prove.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG),
        help="metric catalog YAML (defaults to the repository path)",
    )
    prove.add_argument(
        "--formulas",
        default=str(DEFAULT_FORMULAS),
        help="metric formulas YAML (defaults to the repository path)",
    )
    prove.add_argument("--out", default=None, help="write the JSON report here")
    prove.add_argument(
        "--print",
        dest="print_block",
        action="store_true",
        help="write the fixed print block to stderr",
    )
    prove.add_argument(
        "--require-acceptance",
        action="store_true",
        help="exit 4 when the report is not acceptance-eligible",
    )
    args = parser.parse_args(argv)
    try:
        return _run_prove(args)
    except CoverageProofError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
