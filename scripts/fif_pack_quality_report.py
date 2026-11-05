#!/usr/bin/env python3
"""FIF Q1 — write one specialist-pack quality report from label/prediction JSON.

Thin CLI over the pure scoring core
(``engine/fundamental_forensics/pack_evaluation.py``). Reads exactly two JSON
files (a list of label-record objects and a list of prediction-record objects)
plus the frozen Q0 protocol manifest under ``--protocol-root``; writes exactly
``--out`` and ``--out.power.json``; prints the evaluation gaps. It never globs
or opens a directory, never names the sealed proof root (split roots reach the
report only through the protocol manifest at runtime), and never reads the
process environment.

Usage (from the repo root, offline, deterministic):

    python3 scripts/fif_pack_quality_report.py \
        --protocol-root . --pack PK01 --split held_out \
        --labels labels.json --predictions predictions.json \
        --head-commit <40-hex-sha> --evaluated-at 2026-10-19T00:00:00Z \
        --out report.json [--precision-floor 0.9] [--blocked-pack PK03]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields, replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.fundamental_forensics.pack_evaluation import (  # noqa: E402
    LabelRecord,
    PackEvaluationError,
    PredictionRecord,
    evaluate_pack,
    load_q0_protocol,
)

_SPLITS = ("gold", "held_out")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fif_pack_quality_report",
        description=(
            "Score one specialist pack on one split against the frozen Q0 "
            "quality protocol and write the pack quality report."
        ),
    )
    parser.add_argument(
        "--protocol-root",
        required=True,
        help="repository root holding research/financial_intelligence_fabric/",
    )
    parser.add_argument("--pack", required=True, help="pack id PK01..PK12")
    parser.add_argument("--split", required=True, choices=_SPLITS)
    parser.add_argument(
        "--labels", required=True, help="JSON file: list of label-record objects"
    )
    parser.add_argument(
        "--predictions",
        required=True,
        help="JSON file: list of prediction-record objects",
    )
    parser.add_argument("--head-commit", required=True, help="40-hex commit sha")
    parser.add_argument("--evaluated-at", required=True, help="ISO-8601 UTC string")
    parser.add_argument("--out", required=True, help="report output JSON path")
    parser.add_argument(
        "--precision-floor",
        default=None,
        help="predeclared extraction-precision Wilson lower-bound floor (decimal)",
    )
    parser.add_argument(
        "--blocked-pack",
        action="append",
        default=[],
        metavar="PKnn",
        help="pack id under blocked-pack disposition (repeatable)",
    )
    return parser


def _load_rows(path: str) -> list[dict]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not all(
        isinstance(row, dict) for row in rows
    ):
        raise SystemExit(f"{path}: expected a JSON list of objects")
    return rows


def _record(cls, row: dict):
    names = {field.name for field in fields(cls)}
    unknown = sorted(set(row) - names)
    if unknown:
        raise SystemExit(f"{cls.__name__}: unknown field(s) {unknown}")
    try:
        record = cls(**row)
    except TypeError as exc:
        raise SystemExit(f"{cls.__name__}: {exc}") from exc
    if isinstance(record, PredictionRecord) and isinstance(
        record.display_copy, list
    ):
        record = replace(record, display_copy=tuple(record.display_copy))
    return record


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.precision_floor is not None:
        try:
            precision_floor: Decimal | None = Decimal(args.precision_floor)
        except InvalidOperation:
            raise SystemExit(
                f"--precision-floor {args.precision_floor!r} is not a decimal"
            ) from None
    else:
        precision_floor = None
    protocol = load_q0_protocol(args.protocol_root)
    labels = [
        _record(LabelRecord, row) for row in _load_rows(args.labels)
    ]
    predictions = [
        _record(PredictionRecord, row) for row in _load_rows(args.predictions)
    ]
    try:
        result = evaluate_pack(
            labels,
            predictions,
            protocol=protocol,
            pack_id=args.pack,
            split=args.split,
            head_commit=args.head_commit,
            evaluated_at=args.evaluated_at,
            precision_floor=precision_floor,
            blocked_pack_ids=tuple(args.blocked_pack),
        )
    except PackEvaluationError as exc:
        print(f"pack evaluation refused: {exc}", file=sys.stderr)
        return 1
    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(result.report, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    out_path.with_name(out_path.name + ".power.json").write_text(
        json.dumps(list(result.power_checks), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for gap in result.gaps:
        print(f"GAP: {gap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
