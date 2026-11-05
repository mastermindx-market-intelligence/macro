"""Discover exact local concepts and curation gaps in the existing GMI graph."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.theme_graph import store
from engine.theme_graph.ontology import RepositoryStore
from engine.theme_graph.ontology_inventory import compose_inventory, render_markdown, MAPPINGS, CURATIONS


def source_paths():
    return [store.nodes_path(), store.edges_path(), store.node_lifecycle_path(), store.probation_path()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--knowledge-cutoff")
    parser.add_argument("--source-family", help="exact owner family, not a label search")
    parser.add_argument("--mapping", choices=sorted(MAPPINGS), default="all")
    parser.add_argument("--curation", choices=sorted(CURATIONS), default="all")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--snapshot", help="first-page digest, required for continued pages")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--out", help="new output file only; existing paths are never overwritten")
    args = parser.parse_args(argv)
    try:
        for source in source_paths():
            if not source.is_file():
                raise FileNotFoundError(f"required graph input unavailable: {source.name}")
        if args.out and Path(args.out).exists():
            raise ValueError("output must be a new file")
        result = compose_inventory(RepositoryStore(), asof=args.asof, knowledge_cutoff=args.knowledge_cutoff,
            source_family=args.source_family, mapping=args.mapping, curation=args.curation,
            limit=args.limit, offset=args.offset, expected_snapshot=args.snapshot)
        text = render_markdown(result) if args.format == "markdown" else json.dumps(
            result, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        if args.out:
            with Path(args.out).open("x", encoding="utf-8") as stream:
                stream.write(text)
        else:
            print(text, end="")
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "code": "ONTOLOGY_INVENTORY_UNAVAILABLE", "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
