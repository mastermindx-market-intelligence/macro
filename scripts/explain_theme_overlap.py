"""Explain company membership overlap in an existing GMI proposal-review export.

python3 scripts/explain_theme_overlap.py --review review.json --format markdown
Input: query_theme_ontology.py --proposal-id ...; this command never queries the graph.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.theme_graph.membership_evidence import build_overlap_evidence, render_markdown
from scripts.explain_theme_changes import _load


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--review", required=True, help="existing exact proposal-review JSON")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--out", help="new output file only; existing paths are never overwritten")
    args = parser.parse_args(argv)
    try:
        source = Path(args.review)
        output = Path(args.out) if args.out else None
        if output and (output.resolve() == source.resolve() or output.exists()):
            raise ValueError("output must be a new path, not the input or an existing file")
        document = _load(source)
        report = build_overlap_evidence(document)
        text = (render_markdown(report) if args.format == "markdown" else
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")
        if output is None:
            print(text, end="")
        else:
            with output.open("x", encoding="utf-8") as stream:
                stream.write(text)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({"schema": "gmi.theme_overlap_refusal/v1", "ok": False,
                          "code": "OVERLAP_EVIDENCE_UNAVAILABLE", "message": str(exc)},
                         sort_keys=True), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
