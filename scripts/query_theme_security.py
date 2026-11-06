"""Navigate exact published security/issuer references to GMI graph neighborhoods.

Example: python3 scripts/query_theme_security.py --security-id SEC:US-XNAS-SNDK
         --asof 2026-09-20 [--knowledge-cutoff 2026-09-20] [--out new-export.json]
Identity references are the latest published owner snapshot, NOT historical identity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.theme_graph import identity_resolution as identity_owner  # noqa: E402
from engine.theme_graph.ontology import RepositoryStore  # noqa: E402
from engine.theme_graph.security_navigation import compose_security_neighborhoods  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--security-id", help="exact Data OS SEC: identity; no ticker lookup")
    target.add_argument("--issuer-id", help="exact Data OS ISS: identity; no name lookup")
    parser.add_argument("--asof", required=True, help="graph effective date only")
    parser.add_argument("--knowledge-cutoff", help="graph knowledge date only; defaults to --asof")
    parser.add_argument("--out", help="new export file; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        rows = identity_owner.read_identity_resolution(latest=True)
        result = compose_security_neighborhoods(RepositoryStore(), rows,
            identity_kind="security" if args.security_id else "issuer",
            identity_id=args.security_id or args.issuer_id, asof=args.asof,
            knowledge_cutoff=args.knowledge_cutoff)
        text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as output:
                output.write(text)
        else:
            print(text, end="")
    except (OSError, RuntimeError, TypeError, ValueError, KeyError) as exc:
        print(json.dumps({"schema": "gmi.theme_security_neighborhood_refusal/v1",
            "ok": False, "code": "SECURITY_QUERY_UNAVAILABLE", "message": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
