"""Query one exact GMI ontology neighborhood without promoting probation proposals.

Run:
  python -m scripts.query_theme_ontology --node-id <exact-id> --asof YYYY-MM-DD
      [--knowledge-cutoff YYYY-MM-DD] [--out path.json]
  Replace --node-id with --proposal-id to inspect one proposal and its exact endpoints.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.theme_graph.ontology import (  # noqa: E402
    RepositoryStore, compose_neighborhood, compose_proposal_review,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--node-id", help="exact graph node_id; no label search")
    target.add_argument("--proposal-id", help="exact probation proposal_id; read-only evidence review")
    parser.add_argument("--asof", required=True, help="effective date (YYYY-MM-DD)")
    parser.add_argument(
        "--knowledge-cutoff",
        help="belief cutoff (YYYY-MM-DD); defaults to --asof",
    )
    parser.add_argument("--out", help="optional JSON output path; stdout otherwise")
    args = parser.parse_args(argv)
    try:
        query = compose_proposal_review if args.proposal_id else compose_neighborhood
        identity = {"proposal_id": args.proposal_id} if args.proposal_id else {"node_id": args.node_id}
        result = query(
            RepositoryStore(),
            **identity,
            asof=args.asof,
            knowledge_cutoff=args.knowledge_cutoff,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema": "gmi.theme_ontology_neighborhood_refusal/v1",
                    "ok": False,
                    "code": "ONTOLOGY_QUERY_UNAVAILABLE",
                    "message": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
