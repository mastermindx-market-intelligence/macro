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
from engine.theme_graph.membership_evidence import (
    build_overlap_evidence, render_markdown,
    build_microtheme_research_evidence, render_microtheme_research_markdown,
    build_microtheme_identity_preflight, render_microtheme_identity_preflight_markdown,
)
from scripts.explain_theme_changes import _load


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--review", help="existing exact proposal-review JSON")
    sources.add_argument("--microtheme-research", help="pinned, unadmitted GMI microtheme research JSON")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--issuer-reference", help="current Data OS issuer_master.parquet for non-admitting identity hint triage")
    parser.add_argument("--security-reference", help="current Data OS security_master.parquet; no PIT issuer claim")
    parser.add_argument("--out", help="new output file only; existing paths are never overwritten")
    args = parser.parse_args(argv)
    try:
        name = args.review if args.review is not None else args.microtheme_research
        if not name:
            raise ValueError("source path must not be empty")
        source = Path(name)
        output = Path(args.out) if args.out else None
        if output and (output.resolve() == source.resolve() or output.exists()):
            raise ValueError("output must be a new path, not the input or an existing file")
        identity_mode = args.issuer_reference is not None or args.security_reference is not None
        if identity_mode and (args.microtheme_research is None
                              or not args.issuer_reference or not args.security_reference):
            raise ValueError("identity reference triage requires both Data OS files and --microtheme-research")
        document = _load(source)
        if args.microtheme_research is not None:
            if identity_mode:
                import hashlib
                import stat
                try:
                    import pyarrow.parquet as pq
                except ImportError as exc:
                    raise ValueError("Data OS parquet reader unavailable") from exc
                inputs = []
                for name in (args.issuer_reference, args.security_reference):
                    target = Path(name)
                    info = target.lstat()
                    if not stat.S_ISREG(info.st_mode) or info.st_size > 4_000_000:
                        raise ValueError("unsafe or oversized Data OS reference")
                    if output is not None and output.resolve() == target.resolve():
                        raise ValueError("output cannot overwrite a Data OS reference")
                    raw = target.read_bytes()
                    inputs.append((pq.read_table(target).to_pylist(), hashlib.sha256(raw).hexdigest()))
                report = build_microtheme_identity_preflight(
                    document, issuer_rows=inputs[0][0], security_rows=inputs[1][0],
                    issuer_snapshot_sha256=inputs[0][1], security_snapshot_sha256=inputs[1][1],
                )
            else:
                report = build_microtheme_research_evidence(document)
        else:
            report = build_overlap_evidence(document)
        text = (render_microtheme_identity_preflight_markdown(report)
                if identity_mode and args.format == "markdown"
                else render_microtheme_research_markdown(report)
                if args.microtheme_research is not None and args.format == "markdown"
                else render_markdown(report) if args.format == "markdown"
                else json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")
        if output is None:
            print(text, end="")
        else:
            with output.open("x", encoding="utf-8") as stream:
                stream.write(text)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({"schema": ("gmi.microtheme_membership_review_refusal/v1"
                                       if args.microtheme_research is not None
                                       else "gmi.theme_overlap_refusal/v1"), "ok": False,
                          "code": ("MICROTHEME_RESEARCH_UNAVAILABLE"
                                   if args.microtheme_research is not None
                                   else "OVERLAP_EVIDENCE_UNAVAILABLE"), "message": str(exc)},
                         sort_keys=True), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
