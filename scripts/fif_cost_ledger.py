#!/usr/bin/env python3
"""FIF V1-b — cost and operator-burden ledger CLI.

Builds the node V1 cost ledger (cost per qualified filing/issuer/query and
operator burden) from the census economics receipt, the deep-packages CSV and
the repository ai_costs usage ledger, using only declared rates.  An omitted
input gives an ``unmeasured`` component — it never defaults to 0.

Usage (from the repo root, offline):

    python3 scripts/fif_cost_ledger.py build \
        --rates config/fundamental_forensics/cost_rates.v1.json \
        --built-at 2026-10-19T00:00:00Z \
        --economics economics.json --deep-packages deep_packages.csv \
        --ai-usage usage.jsonl --licence-issuers 1000 \
        --denominators denominators.json \
        --out cost_ledger.json --print

    python3 scripts/fif_cost_ledger.py burden-append \
        --burden burden.jsonl --row-json '<one operator_burden/v1 row>'

Exit codes: 0 computed (complete or not); 2 refusal; 5 --require-complete
was given and the ledger is not complete.  ``--print`` writes the human
summary to stderr so stdout stays clean for piping.

Laws this tool enforces on itself: no network, no wall-clock read (built_at
is an argument), every input read is bounded by HARD_MAX_INPUT_BYTES, and a
missing burden file means review minutes are unmeasured rather than zero.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.fundamental_forensics.cost_ledger import (  # noqa: E402
    CostLedgerError,
    Quantity,
    append_burden,
    build_cost_ledger,
    inference_quantity_from_usage,
    licence_quantity,
    load_rates,
    parse_quantity,
    read_burden,
    read_text_bounded,
    render_print,
    review_quantity_from_burden_rows,
    source_quantity_from_receipt,
    storage_quantity_from_deep_packages,
    UNMEASURED,
)

_DENOMINATOR_KEYS = (
    "qualified_filings",
    "qualified_issuers_deep",
    "qualified_issuers_core",
    "queries",
)


def _omitted_quantity(unit: str) -> Quantity:
    return Quantity(None, unit, UNMEASURED, notes=("input_omitted",), counts={})


def _parse_built_at(text: str) -> datetime:
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CostLedgerError("built_at_shape", f"--built-at is not an ISO instant: {exc}")
    if moment.tzinfo is None:
        raise CostLedgerError("built_at_shape", "--built-at must carry a UTC designator")
    return moment


def _load_json(path: str, refusal_code: str) -> dict:
    text = read_text_bounded(path)
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CostLedgerError(refusal_code, f"{path} is not JSON: {exc}")
    if not isinstance(doc, dict):
        raise CostLedgerError(refusal_code, f"{path} must hold a JSON object")
    return doc


def _default_denominators() -> dict:
    denominators = {
        key: {"value": None, "source": "denominators_not_provided"}
        for key in _DENOMINATOR_KEYS
    }
    denominators["queries"]["window"] = None
    return denominators


def _cmd_build(args: argparse.Namespace) -> int:
    rates = load_rates(args.rates)

    if args.economics:
        receipt = _load_json(args.economics, "receipt_shape")
        quantities = {"source": source_quantity_from_receipt(receipt)}
    else:
        quantities = {"source": _omitted_quantity("get")}

    if args.deep_packages:
        quantities["storage"] = storage_quantity_from_deep_packages(
            read_text_bounded(args.deep_packages)
        )
    else:
        quantities["storage"] = _omitted_quantity("gb")

    if args.denominators:
        denominators = _load_json(args.denominators, "denominators_shape")
    else:
        denominators = _default_denominators()

    # The inference rows are tied to the queries counting window, the same
    # window the queries denominator declares; without it the rows are not
    # filtered and cost-per-query is refused (queries_window_absent).
    queries_entry = denominators.get("queries") if isinstance(denominators, dict) else None
    queries_window = queries_entry.get("window") if isinstance(queries_entry, dict) else None

    if args.ai_usage:
        usage_text = read_text_bounded(args.ai_usage)
        quantities["inference"] = inference_quantity_from_usage(
            usage_text.splitlines(), rates["inference_row_filter"], window=queries_window
        )
    else:
        quantities["inference"] = _omitted_quantity("usd")

    quantities["parse"] = parse_quantity(args.parse_cpu_seconds)
    quantities["licence"] = licence_quantity(args.licence_issuers)

    if args.burden is None:
        burden_rows = None
    elif os.path.exists(args.burden):
        burden_rows = read_burden(args.burden)
    else:
        # A burden path whose file does not exist yet means there is no file:
        # review minutes are unmeasured, never zero.
        burden_rows = None
    quantities["review"] = review_quantity_from_burden_rows(burden_rows)

    built_at = _parse_built_at(args.built_at)
    ledger = build_cost_ledger(
        rates=rates,
        quantities=quantities,
        denominators=denominators,
        burden_rows=burden_rows,
        built_at=built_at,
    )

    if args.out:
        out_path = Path(args.out)
        if out_path.parent and not out_path.parent.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
        try:
            out_path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            raise CostLedgerError("out_unwritable", f"cannot write {args.out}: {exc}")

    if args.print:
        print(render_print(ledger), file=sys.stderr)

    if args.require_complete and not ledger["complete"]:
        print(
            "fif-cost-ledger: ledger is not complete "
            f"(one_time incomplete: {ledger['totals']['one_time']['incomplete_components']}; "
            f"per_month incomplete: {ledger['totals']['per_month']['incomplete_components']}; "
            f"query_window incomplete: {ledger['totals']['query_window']['incomplete_components']})",
            file=sys.stderr,
        )
        return 5
    return 0


def _cmd_burden_append(args: argparse.Namespace) -> int:
    try:
        row = json.loads(args.row_json)
    except json.JSONDecodeError as exc:
        raise CostLedgerError("burden_shape", f"--row-json is not JSON: {exc}")
    append_burden(args.burden, row)
    event_id = row.get("event_id") if isinstance(row, dict) else None
    print(f"appended event_id={event_id!r} to {args.burden}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fif_cost_ledger.py",
        description="FIF cost and operator-burden ledger (node V1).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build a cost ledger")
    build.add_argument("--rates", required=True, help="rates config JSON path")
    build.add_argument("--built-at", required=True, help="ISO Z instant of this build")
    build.add_argument("--economics", help="census economics receipt JSON")
    build.add_argument("--deep-packages", help="deep packages census CSV")
    build.add_argument("--ai-usage", help="ai_costs usage JSONL")
    build.add_argument(
        "--parse-cpu-seconds", type=float, default=None, help="measured parse CPU seconds"
    )
    build.add_argument(
        "--licence-issuers", type=int, default=None, help="issuers covered by the licence"
    )
    build.add_argument("--burden", help="operator-burden JSONL ledger")
    build.add_argument("--denominators", help="denominators JSON")
    build.add_argument("--out", help="write the ledger JSON here")
    build.add_argument(
        "--print", action="store_true", help="print the human summary to stderr"
    )
    build.add_argument(
        "--require-complete",
        action="store_true",
        help="exit 5 when the ledger is not complete",
    )
    build.set_defaults(handler=_cmd_build)

    burden_append = subparsers.add_parser(
        "burden-append", help="append one row to the burden ledger"
    )
    burden_append.add_argument("--burden", required=True, help="burden JSONL path")
    burden_append.add_argument("--row-json", required=True, help="one burden row as JSON")
    burden_append.set_defaults(handler=_cmd_burden_append)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except CostLedgerError as exc:
        print(f"fif-cost-ledger: refusal {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
