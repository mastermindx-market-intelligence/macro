"""Offline specialist-pack producer CLI.

Loads committed golden filing-package directories, produces one
``specialist_pack_result.v1`` envelope through the producer registry and
writes it as canonical JSON. No network, no environment reads, no wall clock
in the output.

Exit codes: 0 valid envelope (any applicability state), 2 usage errors,
1 production refusal.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.fundamental_forensics.specialist_packs import (  # noqa: E402
    PackInput,
    SpecialistPackError,
    produce_pack,
)
from engine.fundamental_forensics.statement_graph import (  # noqa: E402
    StatementGraphError,
    admit_golden_aapl_package,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fif_specialist_packs",
        description="Produce one specialist pack result envelope offline.",
    )
    parser.add_argument("--pack", required=True, help="pack id, e.g. PK06")
    parser.add_argument(
        "--package-dir",
        action="append",
        required=True,
        dest="package_dirs",
        help="admitted filing package directory (repeatable)",
    )
    parser.add_argument(
        "--entity-json", required=True, help="packet entity object JSON file"
    )
    parser.add_argument(
        "--query-json", required=True, help="packet query object JSON file"
    )
    parser.add_argument(
        "--issuer-sic", default=None, help="issuer SIC digit string"
    )
    parser.add_argument(
        "--sic-source",
        choices=("sec_submissions", "dei", "unbound"),
        default=None,
    )
    parser.add_argument("--packet-id", default=None, help="fip_ packet id")
    parser.add_argument("--out", required=True, help="output JSON path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        entity = json.loads(Path(args.entity_json).read_text(encoding="utf-8"))
        query = json.loads(Path(args.query_json).read_text(encoding="utf-8"))
        packages = [
            admit_golden_aapl_package(Path(item)) for item in args.package_dirs
        ]
        pack_input = PackInput(
            packages=tuple(packages),
            entity=entity,
            query=query,
            issuer_sic=args.issuer_sic,
            sic_source=args.sic_source,
            packet_id=args.packet_id,
        )
        result = produce_pack(args.pack, pack_input)
    except SpecialistPackError as exc:
        print(f"specialist pack refused: {exc}", file=sys.stderr)
        return 1
    except RecursionError as exc:
        # R-F5 belt-and-braces: the framework's cross-pack cycle guard cuts
        # cycles before recursion; if one still escapes, refuse loudly.
        print(f"specialist pack refused: {type(exc).__name__}", file=sys.stderr)
        return 1
    except (StatementGraphError, OSError, ValueError, KeyError) as exc:
        print(f"input refused: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    Path(args.out).write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
