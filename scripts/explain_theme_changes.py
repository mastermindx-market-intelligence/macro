"""Explain two GMI neighborhood exports as JSON or a human research brief.

Existing query_theme_ontology.py produces the input documents; this tool reads only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.theme_graph.change_report import build_change_report, render_markdown

MAX_INPUT_BYTES = 8 * 1024 * 1024


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds the 8 MiB document limit")
    return json.loads(raw, object_pairs_hook=_unique_object)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", required=True, help="existing baseline neighborhood JSON")
    parser.add_argument("--target", required=True, help="existing target neighborhood JSON")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--out", help="new output file; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        if args.out and Path(args.out).resolve() in {Path(args.baseline).resolve(), Path(args.target).resolve()}:
            raise ValueError("output must not replace an input document")
        report = build_change_report(_load(args.baseline), _load(args.target))
        text = render_markdown(report) if args.format == "markdown" else json.dumps(
            report, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        if args.out:
            with Path(args.out).open("x", encoding="utf-8") as stream:
                stream.write(text)
        else:
            print(text, end="")
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "code": "CHANGE_REPORT_UNAVAILABLE", "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
