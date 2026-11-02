"""Browse the existing GMI probation queue without approving or rewriting proposals."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.theme_graph import probation, store
from engine.theme_graph.proposal_worklist import compose_worklist, render_markdown


def proposal_path():
    return store.probation_path()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", required=True, help="effective date carried to evidence drilldown")
    parser.add_argument("--knowledge-cutoff", help="proposal knowledge cutoff; defaults to asof")
    parser.add_argument("--status", choices=sorted(probation.STATUSES | {"all"}), default="proposed")
    parser.add_argument("--kind", choices=sorted(probation.PROPOSAL_KINDS))
    parser.add_argument("--proposed-by", choices=sorted(probation.PROPOSED_BY))
    parser.add_argument("--subject-id", help="exact structured subject ID; no label search")
    parser.add_argument("--limit", type=int, default=25, help="page size, 1..100")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--snapshot", help="first page digest, required for subsequent pages")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--out", help="new output file; existing paths are never overwritten")
    args = parser.parse_args(argv)
    try:
        path = proposal_path()
        if args.out and Path(args.out).resolve() == path.resolve():
            raise ValueError("output must not replace the probation source")
        rows = probation.read_proposals(path, strict=True)
        result = compose_worklist(rows, asof=args.asof, knowledge_cutoff=args.knowledge_cutoff,
            status=args.status, kind=args.kind, proposed_by=args.proposed_by,
            subject_id=args.subject_id, limit=args.limit, offset=args.offset,
            expected_snapshot=args.snapshot)
        text = render_markdown(result) if args.format == "markdown" else json.dumps(
            result, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        if args.out:
            with Path(args.out).open("x", encoding="utf-8") as stream:
                stream.write(text)
        else:
            print(text, end="")
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "code": "PROPOSAL_WORKLIST_UNAVAILABLE", "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
